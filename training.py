import torch
import os
import random
from model.model_interpol import ColorCNN 
import glob, os
from torch.utils.tensorboard import SummaryWriter
import cv2
from dataset.multiproc_dataset import MultiProcDataset
from dataset.imagenet_dataset import ImageDataset
import string
from torchvision import transforms


def loadVideos(path):
    # load all .mp4-files from path into list
    train_list = path + "/train_filenames.txt"
    test_list  =path + "/test_filenames.txt"

    f = open(train_list, "r")
    training_names = f.readlines()
    training_names = [x.strip() for x in training_names]
    f.close()

    f = open(test_list, "r")
    test_names = f.readlines()
    test_names = [x.strip() for x in test_names]
    f.close()
    return training_names, test_names

def train(model, train_loader, criterion, optimizer, writer, stepsTilNow=0):
    i = 0
    '''
    for name, param in model.named_parameters():
        if param.requires_grad:
            writer.add_histogram(name, param, -1) 
            i += 1
    '''
    model.train()
    step = 0
    transform = transforms.Compose([
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                            std=[0.229, 0.224, 0.225])])
    for batch in train_loader:
        first_it = batch[1]
        resnet_in = batch[2]
        batch = batch[0]
    
        resnet_in = resnet_in.cuda(non_blocking=True)
        for i in range(resnet_in.shape[0]):
            resnet_in[i] = transform(resnet_in[i])

        x_in = batch[:,:,:,:,0].unsqueeze(dim=4).cuda(non_blocking=True)


        # y_out_shape (batchsize, sequence_length, height, width, num_channels)

        y_out_a = batch[:,:,:,:,1].unsqueeze(dim=4).permute(0,1,4,2,3).cuda(non_blocking=True)
        y_out_b = batch[:,:,:,:,2].unsqueeze(dim=4).permute(0,1,4,2,3).cuda(non_blocking=True)

        model_out = model(x_in, first_it, resnet_in)
        # out (batchsize, sequencelength, num_channels, height, width)

        l1 = criterion(model_out[:,:,0].unsqueeze(dim=2), y_out_a)
        l2 = criterion(model_out[:,:,1].unsqueeze(dim=2), y_out_b)
        loss = (l1 + l2) / 2
        #sequenceLength = x_in.shape[1]
        #batchsize = x_in.shape[0]
        #loss /= (sequenceLength * batchsize)

        writer.add_scalar('LOSS', loss, step)
        '''
        if step % 100 == 0:
            i = 0
            for name, param in model.named_parameters():
                if param.requires_grad:
                    writer.add_histogram(name, param, step) 
                    i += 1
        '''
        optimizer.zero_grad()
        loss.backward() 
        optimizer.step()
        stepsTilNow += 1
        step += 1
        if step % 100 == 0:
            torch.save(model.state_dict(), "/network-ceph/pgrundmann/video_model_gru_steps_" + str(step) + ".bin") 

def evaluate(model, epoch,test_loader,criterion, writer):
    losses = torch.empty(0)
    with torch.no_grad():
        model.eval()
        for batch in test_loader:
            x_in = batch[0].cuda()
            y_out_a = batch[1].cuda()
            y_out_b = batch[2].cuda()
            mask = batch[3].cuda()

            model_out = model(x_in)
            model_out *= mask
            l1 = criterion(model_out(model_out[:,0], y_out_a))
            l2 = criterion(model_out(model_out[:,1], y_out_b))
            loss = (l1 + l2) / 2
            losses = torch.stack((losses,loss),dim=0)

    acc = torch.mean(losses, dim=0)
    writer.add_scalar("Accuracy",acc,epoch)

def custom_cross_entropy(weights, input, target):
    x = target * torch.log(input)
    x = x * weights
    x = x.sum()
    return -x

def main():
    torch.multiprocessing.set_start_method('spawn')
    end = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    config_name = "VIDEO-MODEL-CNN-ONLY" + end
    writer = SummaryWriter(log_dir="/network-ceph/pgrundmann/video_runs/" +config_name+"/",max_queue=20)

    BATCH_SIZE=64
    SEQUENCE_LENGTH=1
    EPOCHS=1
    LR = 0.0001
    criterion = custom_cross_entropy
    path = '/network-ceph/pgrundmann/youtube_processed'

    training_videos, test_videos = loadVideos(path)

    dataset = MultiProcDataset(training_videos, batchsize=BATCH_SIZE, sequence_length=SEQUENCE_LENGTH)
    train_loader = torch.utils.data.DataLoader(dataset,batch_size=None, num_workers=0, pin_memory=True)
  
    model = ColorCNN()
    model = model.cuda()
    
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, eps=1e-8)

    for i in range(EPOCHS):
        train(model,train_loader, criterion, optimizer, writer)
        print("Epoch finished")
        torch.save(model.state_dict(), "/network-ceph/pgrundmann/video_model_" + str(i) + ".bin")
   #     evaluate(model,(i+1), test_loader,criterion,writer)



if __name__ == "__main__":

    main()




