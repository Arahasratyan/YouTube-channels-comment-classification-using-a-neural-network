import os
import numpy as np
import re
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
from gensim.models import KeyedVectors
from tqdm import tqdm
import torch
import torch.utils.data as data
import torch.nn as nn
import torch.optim as optim


#downloading embeding model in the first use

#import gensim.downloader as api
# print("Downloading model...")
# glove_vectors = api.load("glove-twitter-100")
#
# glove_vectors.save("glove_twitter_100.kv")
# print("Saved to local directory.")


class CommentDataset(data.Dataset):
    def __init__(self, chanel1_path, chanel2_path, emb, batch_size=32, test_size=0.1, random_state=5):
        self.emb = emb
        self.batch_size = batch_size

        chanel_1_vieos = os.listdir(chanel1_path)
        chanel_2_vieos = os.listdir(chanel2_path)

        comments_1, comments_2 = [], []

        for vieo_txt in chanel_1_vieos:
            with open(os.path.join(chanel1_path, vieo_txt), "r", encoding='utf-8') as f:
                comments = f.readlines()
                self._clear_phrase(comments)
                for c in comments:
                    if len(c) > 0:
                        comments_1.append(c)

        for vieo_txt in chanel_2_vieos:
            with open(os.path.join(chanel2_path, vieo_txt), "r", encoding='utf-8') as f:
                comments = f.readlines()
                self._clear_phrase(comments)
                for c in comments:
                    if len(c) > 0:
                        comments_2.append(c)

        full_comment_lst = [(_x, 0) for _x in comments_1] + [(_x, 1) for _x in comments_2]

        train_lst, test_lst = train_test_split(
            full_comment_lst,
            test_size=test_size,
            random_state=random_state,
            stratify=[pair[1] for pair in full_comment_lst]
        )

        self.comment_lst = train_lst
        self.comment_lst.sort(key=lambda _x: len(_x[0]))
        self.dataset_len = len(self.comment_lst)

        self.test_list = test_lst
        self.test_list.sort(key=lambda _x: len(_x[0]))

    def _clear_phrase(self, p_lst):
        for _i, _p in enumerate(p_lst):
            _p = _p.lower().replace('\ufeff', '').strip()
            _p = re.sub(r'[^А-яA-z- ]', '', _p)
            _words = _p.split()
            _words = [w for w in _words if w in self.emb]
            p_lst[_i] = _words

    def __getitem__(self, item):
        item *= self.batch_size
        item_last = item + self.batch_size
        if item_last > self.dataset_len:
            item_last = self.dataset_len

        _data = []
        _target = []
        max_length = len(self.comment_lst[item_last - 1][0])

        for i in range(item, item_last):
            words_emb = []
            phrase = self.comment_lst[i]
            length = len(phrase[0])

            for k in range(max_length):
                t = torch.tensor(self.emb[phrase[0][k]], dtype=torch.float32) if k < length else torch.zeros(100)
                words_emb.append(t)

            _data.append(torch.vstack(words_emb))
            _target.append(torch.tensor(phrase[1], dtype=torch.float32))

        _data_batch = torch.stack(_data)
        _target = torch.vstack(_target)
        return _data_batch, _target

    def __len__(self):
        last = 0 if self.dataset_len % self.batch_size == 0 else 1
        return self.dataset_len // self.batch_size + last


class WordsRNN(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.hidden_size = 16
        self.in_features = in_features
        self.out_features = out_features

        self.rnn = nn.LSTM(in_features, self.hidden_size, batch_first=True, bidirectional=True)
        self.out = nn.Linear(self.hidden_size * 2, out_features)

    def forward(self, x):
        x, (h, c) = self.rnn(x)
        hh = torch.cat((h[-2, :, :], h[-1, :, :]), dim=1)
        y = self.out(hh)
        return y


emb = KeyedVectors.load(r"glove_twitter_100.kv", mmap='r')

d_train = CommentDataset(r"veritasium-and-vsauce-comments/Veritasium",
                         r"veritasium-and-vsauce-comments/Vsauce", emb)
train_data = data.DataLoader(d_train, batch_size=1, shuffle=True)

model = WordsRNN(100, 1)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = model.to(device)
print(device)

if torch.cuda.device_count() > 1:
    print(True, f"There are {torch.cuda.device_count()} GPUs")
    model = nn.DataParallel(model)

optimizer = optim.AdamW(params=model.parameters(), lr=0.001, weight_decay=0.001)
loss_func = nn.BCEWithLogitsLoss()

epochs = 5
model.train()

for _e in range(epochs):
    model.train()
    loss_mean = 0
    lm_count = 0

    train_tqdm = tqdm(train_data, leave=True)
    tmp_var = 0
    for x_train, y_train in train_tqdm:
        try:
            predict = model(x_train.squeeze(0)).squeeze(0)
            loss = loss_func(predict, y_train.squeeze(0))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            lm_count += 1
            loss_mean = 1 / lm_count * loss.item() + (1 - 1 / lm_count) * loss_mean
            train_tqdm.set_description(f"Epoch [{_e + 1}/{epochs}], loss_mean={loss_mean:.3f}")
        except:
            print(f"Error encountered during training step: {e}")

  
    model.eval()
    test_loss = 0
    test_count = 0

    all_y_true = []
    all_y_pred = []

    with torch.no_grad():
        for i in range(0, len(d_train.test_list), d_train.batch_size):
            batch_items = d_train.test_list[i: i + d_train.batch_size]

            # Replicate your __getitem__ padding logic manually
            max_length = len(batch_items[-1][0])

            _data = []
            _target = []
            for phrase in batch_items:
                length = len(phrase[0])
                words_emb = []
                for k in range(max_length):
                    t = torch.tensor(emb[phrase[0][k]], dtype=torch.float32) if k < length else torch.zeros(100)
                    words_emb.append(t)

                _data.append(torch.vstack(words_emb))
                _target.append(torch.tensor(phrase[1], dtype=torch.float32))

            x_test = torch.stack(_data).to(device)
            y_test = torch.vstack(_target).to(device)

            predict_test = model(x_test)
            loss_test = loss_func(predict_test, y_test)

            test_loss += loss_test.item()
            test_count += 1

            probs = torch.sigmoid(predict_test)
            preds = (probs >= 0.5).int()

            all_y_true.extend(y_test.cpu().numpy().flatten())
            all_y_pred.extend(preds.cpu().numpy().flatten())

    epoch_accuracy = accuracy_score(all_y_true, all_y_pred)
    epoch_f1 = f1_score(all_y_true, all_y_pred)
    epoch_test_loss = test_loss / test_count

    print(f"\nTest Loss: {epoch_test_loss:.4f} | ",
          f"Test Acc: {epoch_accuracy * 100:.2f}% | ",
          f"Test F1: {epoch_f1:.4f}\n")

st = model.state_dict()
torch.save(st, 'model_rnn_bidir.tar')

# st = torch.load('model_rnn_bidir.tar')
# model.load_state_dict(st)


# model.eval()
# 
# phrase = "Science is easy!"
# phrase_lst = phrase.lower().split()
# phrase_lst = [torch.tensor(emb[w]) for w in phrase_lst if w in emb]
# _data_batch = torch.stack(phrase_lst)
# predict = model(_data_batch.unsqueeze(0)).squeeze(0)
# p = torch.nn.functional.sigmoid(predict).item()
# print(p)
# print(phrase, ":", "Veritasium" if p < 0.5 else "Vsauce")
