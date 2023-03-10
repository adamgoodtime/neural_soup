import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim
import torchvision
from torchvision import transforms, datasets
import copy

gpu = True
if gpu:
    torch.set_default_tensor_type(torch.cuda.FloatTensor)
    device = 'cuda'
else:
    torch.set_default_tensor_type(torch.FloatTensor)
    device = 'cpu'

input_size = 28 * 28
num_classes = 10
batch_size = 8
num_epochs = 100
lr = 0.008
momentum = 0.9

hidden_size = 128

trainset = datasets.MNIST('', download=True, train=True, transform=transforms.ToTensor())
testset = datasets.MNIST('', download=True, train=False, transform=transforms.ToTensor())
train_loader = torch.utils.data.DataLoader(trainset, batch_size=batch_size,
                                           shuffle=True, generator=torch.Generator(device=device))
test_loader = torch.utils.data.DataLoader(testset, batch_size=batch_size,
                                          shuffle=True, generator=torch.Generator(device=device))


class MyDropout(nn.Module):
    def __init__(self, p: float = 0.5):
        super(MyDropout, self).__init__()
        if p < 0 or p > 1:
            raise ValueError("dropout probability has to be between 0 and 1, " "but got {}".format(p))
        self.p = p

    def forward(self, X):
        if self.training:
            binomial = torch.distributions.binomial.Binomial(probs=1 - self.p)
            bs = binomial.sample(X.size())
            return X * bs * (1.0 / (1 - self.p))
        return X


class MyLinear(nn.Linear):
    def __init__(self, in_feats, out_feats, drop_p, bias=True):
        super(MyLinear, self).__init__(in_feats, out_feats, bias=bias)
        self.custom_dropout = MyDropout(p=drop_p)

    def forward(self, input):
        dropout_value = self.custom_dropout(self.weight)
        return F.linear(input, dropout_value, self.bias)


# Fully connected neural network with one hidden layer
class NeuralNet(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes, p, dropout=True):
        super(NeuralNet, self).__init__()
        if dropout:
            self.fc1 = MyLinear(input_size, hidden_size, p)
        else:
            self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, num_classes)
        self.LogSoftmax = nn.LogSoftmax(dim=1)

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        out = self.LogSoftmax(out)
        nn.Dropout
        return out


# loss_fn = nn.MSELoss(reduction='none')
# input = torch.randn(10, 1, requires_grad=True)
# target = torch.randn(10, 1)
# loss_each = loss_fn(input, target)
# loss_all = torch.mean(loss_each)
# loss_all.backward()
# other_computation(loss_each.detach())

levels_of_dropout = [0.25]

models = {}
params = []
for p in levels_of_dropout:
    models['{}'.format(p)] = NeuralNet(input_size, hidden_size, num_classes, p=p).to(device)
    params.append({'params': models['{}'.format(p)].parameters()})

lossFunction = nn.NLLLoss()
optimize_all = optim.SGD(params,
                         lr=lr, momentum=momentum)


for epoch in range(num_epochs):
    loss_ = [0 for i in range(len(levels_of_dropout))]
    for images, labels in train_loader:
        # Flatten the input images of [28,28] to [1,784]
        images = images.reshape(-1, 784).to(torch.device(device))

        output = []
        for p in models:
            output.append(models[p](images))

        loss = []
        for out in output:
            loss.append(lossFunction(out, labels))

        optimize_all.zero_grad()

        for l in loss:
            l.backward()

        optimize_all.step()

        for i in range(len(levels_of_dropout)):
            loss_[i] += loss[i]

    for i in range(len(levels_of_dropout)):
        print("Epoch{}, Training {} loss:{}".format(epoch, levels_of_dropout[i], loss_[i] / len(train_loader)))

    # Testing
    with torch.no_grad():
        correct = [0 for i in range(len(levels_of_dropout))]
        total = 0
        for images, labels in test_loader:
            images = images.reshape(-1, 784).to(torch.device(device))
            out = []
            for p in models:
                out.append(models[p](images))
            predicted = []
            for o in out:
                _, pred = torch.max(o, 1)
                predicted.append(pred)
            for i in range(len(levels_of_dropout)):
                correct[i] += (predicted[i] == labels).sum().item()
            total += labels.size(0)
        for i in range(len(levels_of_dropout)):
            print('Testing {} accuracy: {} %'.format(levels_of_dropout[i], 100 * correct[i] / total))

# torch.save(model, 'mnist_model.pt')

print('done')