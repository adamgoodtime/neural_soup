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
batch_size = 64
num_epochs = 100
lr = 0.008
momentum = 0.9

hidden_size = 1024

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
            return X * binomial.sample(X.size()) * (1.0 / (1 - self.p))
        return X


class MyLinear(nn.Linear):
    def __init__(self, in_feats, out_feats, drop_p, bias=True, drop_input=True):
        super(MyLinear, self).__init__(in_feats, out_feats, bias=bias)
        self.drop_input = drop_input
        self.custom_dropout = MyDropout(p=drop_p)

    def forward(self, input):
        if self.drop_input:
            dropout_value = self.custom_dropout(input)
            return F.linear(dropout_value, self.weight, self.bias)
        else:
            dropout_value = self.custom_dropout(self.weight)
            return F.linear(input, dropout_value, self.bias)


# Fully connected neural network with one hidden layer
class NeuralNet(nn.Module):
    def __init__(self, input_size, hidden_size, num_classes, p, dropout=True):
        super(NeuralNet, self).__init__()
        # if dropout:
        #     self.fc1 = MyLinear(input_size, hidden_size, p)
        # else:
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        # self.fc2 = nn.Linear(hidden_size, num_classes)
        if dropout:
            self.fc2 = MyLinear(hidden_size, num_classes, p)
        else:
            self.fc2 = nn.Linear(hidden_size, num_classes)
        self.LogSoftmax = nn.LogSoftmax(dim=1)

    def add_neuron(self, rand_init=True):
        with torch.no_grad():
            self.fc1.bias.requires_grad = False
            self.fc1.weight.requires_grad = False
            self.fc2.weight.requires_grad = False

            # self.fc1.bias.requires_grad = True
            # self.fc1.weight.requires_grad = True
            # self.fc2.weight.requires_grad = True

            # self.fc1.bias.detach()
            # self.fc1.weight.detach()
            # self.fc2.weight.detach()

            new_fc1w = torch.vstack([self.fc1.weight.data, torch.zeros([1, input_size])])
            new_fc1b = torch.hstack([self.fc1.bias.data, torch.zeros(1)])
            new_fc2w = torch.hstack([self.fc2.weight.data, torch.zeros([num_classes, 1])])

            # new_fc1w = self.fc1.weight.data
            # new_fc1b = self.fc1.bias.data
            # new_fc2w = self.fc2.weight.data

            out1 = self.fc1.out_features + 1
            in1 = self.fc2.in_features + 1

            # del self.fc1
            # del self.fc2
            # torch.cuda.empty_cache()
            #
            # self.fc1 = nn.Linear(input_size, out1)
            # self.fc2 = MyLinear(in1, num_classes, levels_of_dropout[0])

            self.fc1.weight.data = new_fc1w
            self.fc1.bias.data = new_fc1b
            self.fc2.weight.data = new_fc2w


            self.fc1.bias.requires_grad = True
            self.fc1.weight.requires_grad = True
            self.fc2.weight.requires_grad = True

            # self.fc1.weight = nn.Parameter(torch.zeros_like(self.fc1.weight, requires_grad=False))
            # self.fc1.bias = nn.Parameter(torch.zeros_like(self.fc1.bias, requires_grad=False))
            # self.fc1.out_features += 1
            # self.fc2.weight = nn.Parameter(torch.zeros_like(self.fc2.weight, requires_grad=False))
            # self.fc2.in_features += 1
            # param_list_before = []
            # param_list_after = []
            # for param_idx, param in enumerate(self.parameters()):
            #     param_list_before.append(param.data)
            #
            # for param_idx in range(len(param_list_before)):
            #     if param_idx > 1:
            #         param_list_after.append(param_list_before[param_idx])
            #     else:
            #         # param.data = nn.parameter.Parameter(torch.zeros_like(param))
            #         # pre_data = param_list_before[param_idx].data
            #         # post_data = param_list_before[param_idx+2].data
            #         if len(param_list_before[param_idx].data.shape) == 1:
            #             param_list_before[param_idx].data = nn.Parameter(torch.hstack([
            #                 param_list_before[param_idx].data,
            #                 torch.zeros_like(param_list_before[param_idx].data)[0].unsqueeze(0)]),
            #             requires_grad=True)
            #         else:
            #             param_list_before[param_idx].data = nn.Parameter(torch.vstack([
            #                 param_list_before[param_idx].data,
            #                 torch.zeros_like(param_list_before[param_idx].data)[0].unsqueeze(0)]),
            #             requires_grad=True)
            #             param_list_before[param_idx+2].data = nn.Parameter(torch.hstack([
            #                 param_list_before[param_idx+2].data,
            #                 torch.zeros_like(param_list_before[param_idx+2].data)[:, 0].unsqueeze(1)]),
            #             requires_grad=True)
            #         param_list_after.append(param_list_before[param_idx])
            #
            # for param, new_param in zip(self.parameters(), param_list_after):
            #     param.data = new_param
            #
            # param_list = []
            # for param_idx, param in enumerate(self.parameters()):
            #     param_list.append(param.data)

            print("done params")


            # self.fc1.bias.requires_grad = True
            # self.fc1.weight.requires_grad = True
            # self.fc2.weight.requires_grad = True

            # self.fc1.bias.requires_grad = False
            # self.fc1.weight.requires_grad = False
            # self.fc2.weight.requires_grad = False
        # torch.cuda.empty_cache()
    #     # torch.hstack([self.weight, torch.ones([num_classes, 1])])
    #     # self.weight = nn.Parameter(torch.hstack([self.weight, torch.ones([num_classes, 1])]))
    #     self.fc1.weight = nn.Parameter(torch.vstack([self.fc1.weight, torch.ones([1, input_size])]))
    #     self.fc2.weight = nn.Parameter(torch.hstack([self.fc2.weight, torch.ones([num_classes, 1])]))
    #     return self.weight
    # with torch.no_grad():
    #     self.fc1.weight.copy_(torch.vstack([self.fc1.weight, torch.zeros([1, input_size])]))
    #     self.fc1.bias.copy_(torch.hstack([self.fc1.bias, torch.zeros(1)]))
    #     self.fc1.out_features += 1
    #     self.fc2.weight.copy_(torch.hstack([self.fc2.weight, torch.zeros([num_classes, 1])]))
    #     self.fc2.in_features += 1
    # with torch.no_grad():
    #     temp_fc1w = nn.Parameter(torch.vstack([self.fc1.weight, torch.zeros([1, input_size])]))
    #     temp_fc1b = nn.Parameter(torch.hstack([self.fc1.bias, torch.zeros(1)]))
    #     self.fc1.out_features += 1
    #     temp_fc2w = nn.Parameter(torch.hstack([self.fc2.weight, torch.zeros([num_classes, 1])]))
    #     self.fc2.in_features += 1
    #     del self.fc1.weight
    #     del self.fc1.bias
    #     del self.fc2.weight
    #     torch.cuda.empty_cache()
    #     self.fc1.weight = temp_fc1w
    #     self.fc1.bias = temp_fc1b
    #     self.fc2.weight = temp_fc2w
    #     del temp_fc1w
    #     del temp_fc1b
    #     del temp_fc2w
    #     torch.cuda.empty_cache()

    def forward(self, x):
        out = self.fc1(x)
        out = self.relu(out)
        out = self.fc2(out)
        out = self.LogSoftmax(out)
        return out

def check_memory(where=''):
    print(where)
    t = torch.cuda.get_device_properties(0).total_memory
    r = torch.cuda.memory_reserved(0)
    a = torch.cuda.memory_allocated(0)
    f = r - a  # free inside reserved
    print("   total     reserved     allocated     free")
    print(["{0:.2E}".format(thing) for thing in [t, r, a, f]])

levels_of_dropout = [0.3]

models = {}
params = []
for p in levels_of_dropout:
    models['{}'.format(p)] = NeuralNet(input_size, hidden_size, num_classes, p=p).to(device)
    params.append({'params': models['{}'.format(p)].parameters()})

lossFunction = nn.NLLLoss()
optimize_all = optim.SGD(params,
                         lr=lr, momentum=momentum)

training_losses = []
testing_accuracies = []

for epoch in range(num_epochs):
    check_memory("start")
    loss_ = [0 for i in range(len(levels_of_dropout))]
    for batch, (images, labels) in enumerate(train_loader):
        # print("Starting batch", batch+1, "/", len(train_loader))
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

        # check_memory("b")
        # if epoch < 1:
        for p in models:
            models[p].add_neuron()

        # output = []
        # for p in models:
        #     output.append(models[p](images))
        #
        # loss = []
        # for out in output:
        #     loss.append(lossFunction(out, labels))
        #
        # optimize_all.zero_grad()
        #
        # for l in loss:
        #     l.backward()
        #
        # optimize_all.step()
        # check_memory("a")

    for i in range(len(levels_of_dropout)):
        print("Epoch{}, Training {} loss:{}".format(epoch, levels_of_dropout[i], loss_[i] / len(train_loader)))
    training_losses.append(loss_)

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
        testing_accuracies.append(100 * np.array(correct) / total)

# torch.save(model, 'mnist_model.pt')
print("training:")
print(training_losses)
print("testing")
print(testing_accuracies)

print('done')