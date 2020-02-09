import torch
import torch.nn.functional as F
import torch
import torch.nn as nn
import torch.nn.init as init
import torchvision.models as models

from torch.nn import Tanh, ReLU, Sequential, BatchNorm2d, AdaptiveAvgPool2d, Conv2d, MaxPool2d, AvgPool2d, Dropout,ConvTranspose2d
class ColorCNN(torch.nn.Module):

    def __init__(self):
        super(ColorCNN, self).__init__()
        self.enc_conv1 = Conv2d(1, 64, kernel_size=3, stride=2, padding=1)
        self.enc_conv2 = Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.enc_conv3 = Conv2d(128, 128, kernel_size=3, stride=2, padding=1)
        self.enc_conv4 = Conv2d(128, 256, kernel_size=3, stride=1, padding=1)
        self.enc_conv5 = Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        self.enc_conv6 = Conv2d(256, 512, kernel_size=3, stride=2, padding=1)
        self.enc_conv7 = Conv2d(512, 512, kernel_size=3, stride=1, padding=1)
        self.enc_conv8 = Conv2d(512, 512, kernel_size=3, stride=1, padding=1)
        self.enc_pool = AdaptiveAvgPool2d((1,1))

        self.dec_conv1 = Conv2d(1024, 256, kernel_size=1, stride=1, padding=0)
        self.dec_conv2 = Conv2d(256, 128, kernel_size=1, stride=1, padding=0)
        self.dec_conv3 = Conv2d(128, 64, kernel_size=1, stride=1, padding=0)
        self.dec_conv4 = Conv2d(64, 64, kernel_size=3, stride=1, padding=1)
        self.dec_conv5 = Conv2d(64, 32, kernel_size=3, stride=1, padding=1)
        self.dec_conv6 = Conv2d(32, 2, kernel_size=3, stride=1, padding=1)
        
        #self.linear = torch.nn.Linear(256,256)
        #torch.nn.init.kaiming_normal_(self.linear.weight,mode='fan_out', nonlinearity='relu')
        #torch.nn.init.constant_(self.linear.bias, 0.01)
        #self.lstm = torch.nn.LSTM(256, 256, num_layers=2,batch_first=True)

        
        for m in self.modules():
            if isinstance(m, Conv2d):
                torch.nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                torch.nn.init.constant(m.bias, 0.01)
        
        torch.nn.init.xavier_uniform_(self.dec_conv6.weight)
        torch.nn.init.constant_(self.dec_conv6.bias,0.01)
        
        #self.lstm = torch.nn.LSTM(256,256,num_layers=2)

        
        #self.h_n = None
        #self.c_n = None
        #model = EfficientNet.from_pretrained("efficientnet-b4")
        model = models.resnext50_32x4d(pretrained=True)
        model = nn.Sequential(*list(model.children())[:-1]) 
        #model = nn.Sequential(*list(model.children())[:-2])
  
        #modules=list(model.children())[:-1]
        #model=nn.Sequential(*modules)


        self.model = model
        self.model.eval()
        for param in self.model.parameters():
            param.requires_grad = False

    def forward(self, x, first_it, resnet_in):
        '''
        if self.h_n is not None:
            for i in range(first_it.shape[0]):
                if first_it[i] > 0:
                    self.h_n[:,i] = 0
                    self.c_n[:,i] = 0
        '''
        bs = x.shape[0]
        seq_len = x.shape[1]
        x = x.reshape(x.shape[0]*x.shape[1],x.shape[2], x.shape[3], x.shape[4])
        x = x.permute(0,3,1,2)
        ds0_dims = x.size()

        # encoding 
        x = torch.relu(self.enc_conv1(x))
        ds1_dims = x.size()
        x = torch.relu(self.enc_conv2(x))
        x = torch.relu(self.enc_conv3(x))
        ds2_dims = x.size()
        x = torch.relu(self.enc_conv4(x))
        x = torch.relu(self.enc_conv5(x))
        x = torch.relu(self.enc_conv6(x))
        ds3_dims = x.size()
        x = torch.relu(self.enc_conv7(x))
        x = torch.relu(self.enc_conv8(x))
        '''
        pooled_out = []
        pooled_in = x.reshape((bs, x.shape[0] //bs, 256, x.shape[2], x.shape[3])) 
        for i in range(seq_len):
            pooled_out.append(self.enc_pool(pooled_in[:,i]))

        
        pooled_out = torch.stack(pooled_out, dim=0)
        pooled_out = pooled_out.squeeze()
        lstm_in = pooled_out
        if len(lstm_in.shape) == 2:
            lstm_in = lstm_in.unsqueeze(dim=1)
        '''
        # resnet
        scale_factor = 299 / resnet_in.shape[2] 
        resnet_in = torch.nn.functional.interpolate(resnet_in, scale_factor=scale_factor)
        deeplab_out = self.model(resnet_in)
        deeplab_out = deeplab_out.reshape((bs, seq_len,2048, deeplab_out.shape[2], deeplab_out.shape[3]))
        deeplab_out = deeplab_out.reshape((deeplab_out.shape[0]* deeplab_out.shape[1],deeplab_out.shape[2], deeplab_out.shape[3], deeplab_out.shape[4]))
        deeplab_out = torch.nn.functional.interpolate(deeplab_out,(x.shape[2], x.shape[3]))
    

        '''
        if self.h_n is None:
            a, (h_n, c_n) = self.lstm(lstm_in)
            self.h_n = h_n.detach()
            self.c_n = c_n.detach()
        else:
            a, (h_n, c_n) = self.lstm(lstm_in,(self.h_n, self.c_n))
            self.h_n = h_n.detach()
            self.c_n = c_n.detach()
        '''
        #a = torch.relu(self.linear(a))
        #a = a.permute(0,2,1)
        #a = a.reshape(x.shape[0], x.shape[1], 1, 1)
        #a = a.repeat(1,1,x.shape[2], x.shape[3])
        
        #t = torch.cat((a,deeplab_out), dim=1)
        t = torch.cat((deeplab_out,x), dim=1)
        # decoding
        t = torch.relu(self.dec_conv1(t))
        t = torch.relu(self.dec_conv2(t))
        t = torch.nn.functional.interpolate(t, (ds2_dims[2], ds2_dims[3]))

        t = torch.relu(self.dec_conv3(t))
        t = torch.relu(self.dec_conv4(t))
        t = torch.nn.functional.interpolate(t, (ds1_dims[2], ds1_dims[3]))

        t = torch.relu(self.dec_conv5(t))
        t = torch.sigmoid(self.dec_conv6(t))
        t = torch.nn.functional.interpolate(t, (ds0_dims[2], ds0_dims[3]))

        t = t.reshape(bs, t.shape[0] // bs, t.shape[1], t.shape[2], t.shape[3])
        return t
