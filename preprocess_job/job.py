import torch
import random
from skvideo import io
import numpy as np
import cv2
import skvideo
import logging
from sklearn.neighbors import NearestNeighbors
import redis
import h5py
import hdf5plugin

r = redis.Redis(host='redis', port=6379, db=0)
worker_id = r.incr("workerid", amount=1)
finished=0
with h5py.File('/network-ceph/pgrundmann/youtube_precalculated/dataset_' + str(worker_id) + '.hdf5', 'w') as f:

    bins_x = np.arange(start=0,stop=1,step=(1.0/17))
    bins_y = np.arange(start=0,stop=1,step=(1.0/17))
    mesh = np.dstack(np.meshgrid(bins_x, bins_y)).reshape(-1, 2)
    nbrs = NearestNeighbors(n_neighbors=5, algorithm='kd_tree').fit(mesh)
    while(r.llen("videos") > 0):
        video_filename = (r.lpop("videos")).decode('utf-8')
        video_filename_ = '/network-ceph/pgrundmann/youtube_processed_small/' + video_filename
        video = skvideo.io.vread(video_filename_)
        processed_samples = np.zeros((  video.shape[0], 
                                        video.shape[1], 
                                        video.shape[2],
                                        1),
                                        dtype=np.float32)
        sample_histograms = np.zeros((  video.shape[0], 
                                        video.shape[1] * video.shape[2],
                                        17*17),
                                        dtype=np.float32)
        
        resnet_in_all = np.zeros(video.shape, dtype=np.float32)
        for i in range(video.shape[0]):
            frame = video[i]
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2Lab)
            frame = frame.astype(np.float32)
            frame /= 255.0               

            ab = frame[:,:,1:3]
            ab = ab.reshape((ab.shape[0]*ab.shape[1], 2))

            distances, indices = nbrs.kneighbors(ab)
            
            # normalize distances and create reciprocal for one-hot values
            distances = np.power(distances, -1)
            distances_sums = np.sum(distances, axis=1)
            distances_sums = np.expand_dims(distances_sums, axis=1)
            distances /= distances_sums
            distances = np.expand_dims(distances, axis=2)
            
            # create "onehot"-encodings for all pixels based on their distances to the knn
            sample_histograms[i,indices] = distances

            l = frame[:,:,0]
            l = np.expand_dims(l, axis=2)
            resnet_in = np.expand_dims(frame[:,:,0],axis=2)
            resnet_in = np.repeat(resnet_in,3, axis=2)
            resnet_in_all[i] = resnet_in
            processed_samples[i] = l

        print("Calculation finished")
        data_grp = f.create_group(video_filename)
        l_ds = data_grp.create_dataset('images_l', processed_samples.shape, dtype=np.float32, data=processed_samples,**hdf5plugin.Blosc(cname='blosclz', clevel=9, shuffle=hdf5plugin.Blosc.NOSHUFFLE))
        histogram_ds = data_grp.create_dataset('images_hists', sample_histograms.shape, dtype=np.float32, data=sample_histograms, **hdf5plugin.Blosc(cname='blosclz', clevel=9, shuffle=hdf5plugin.Blosc.NOSHUFFLE))
        resnet_ds = data_grp.create_dataset('images_resnet', resnet_in_all.shape, dtype=np.float32, data=resnet_in_all, **hdf5plugin.Blosc(cname='blosclz', clevel=9, shuffle=hdf5plugin.Blosc.NOSHUFFLE))

        l_ds.flush()
        histogram_ds.flush()
        resnet_ds.flush()
        print("Finished: " + str(finished))
        finished += 1
        exit
        '''
        tensor_l = torch.tensor(processed_samples, dtype=torch.float32)
        tensor_hists = torch.tensor(sample_histograms, dtype=torch.float32)
        resnet_in_all = torch.tensor(resnet_in_all,dtype=torch.float32)
        resnet_in_all = resnet_in_all.permute(0,3,1,2)
        combined = [tensor_l, tensor_hists, resnet_in_all]
        torch.save(combined,"/network-ceph/pgrundmann/youtube_precalculated/" + video_filename)
        '''