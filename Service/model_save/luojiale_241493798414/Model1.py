'''
LeNet-1
'''

# usage: python MNISTModel1.py - train the model

from __future__ import print_function

from keras.datasets import mnist
from keras.layers import Convolution2D, MaxPooling2D, Input, Dense, Activation, Flatten
from keras.models import Model
from keras.utils import to_categorical
from keras import backend as K

import numpy as np


def Model1(input_tensor=None, train=False):
    nb_classes = 10
    kernel_size = (5, 5)
    x = Convolution2D(4, kernel_size, activation='relu', padding='same', name='block1_conv1')(input_tensor)
    x = MaxPooling2D(pool_size=(2, 2), name='block1_pool1')(x)
    x = Convolution2D(12, kernel_size, activation='relu', padding='same', name='block2_conv1')(x)
    x = MaxPooling2D(pool_size=(2, 2), name='block2_pool1')(x)
    x = Flatten(name='flatten')(x)
    x = Dense(nb_classes, name='before_softmax')(x)
    x = Activation('softmax', name='predictions')(x)
    model = Model(input_tensor, x)
    return model


if __name__ == '__main__':
    Model1(train=True)
