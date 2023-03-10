# -*- coding: utf-8 -*-
"""Final_SAR.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MlK3wVp0bIq43YS_eL0snGYn00GusVvG

# <p align=center>Detecting Dark Vessels using a Convolutional Neural Network</p>
<p align=center> Patrick Logue </p>

<p align=center><img src="https://drive.google.com/uc?id=1DpQG0RDyXmMhxZv5nJNkd2e-7cBgApEo">
<hr class="solid">

## Introduction

93% of the world's commercial fish stocks are fished at maximum levels or are overfished (UN FAO). As the oceans cannot sustain this level of fishing, the response has been widespread government regulation. An unfortunate consequence of these regulations is the massive uptick in illegal, unreported, and unregulated (IUU) fishing. IUU is one of the greatest threats to the marine ecosystem and biodiversity, contributing heavily to overfishing. IUU fishing vessels circumvent weak governments by shutting off their vessel monitoring systems (VMS) and fishing 'dark'. By not reporting their catch and fishing over quota they threaten the <a href="https://www.fisheries.noaa.gov/insight/understanding-illegal-unreported-and-unregulated-fishing">food security and socioeconomic stability</a> in many developing areas around the world. Organized crime, human rights abuses, forced labor, and piracy are all associated with IUU fishing in an industry estimated to be <a href="https://www.bloomberg.com/news/articles/2022-10-26/chinese-firms-are-driving-illegal-fishing-globally-study-says">worth between \$10 to \$23.5 billion</a>.

What can we do about this issue? To begin, we must detect the illegal activity in order to address it. This is where Synthetic Aperture RADAR (SAR) comes in to play. In the past SAR image was low resolution, intermittent, and expensive but with recent advances in SAR satellite technology we now have access to large amounts of high-quality SAR imagery. The incredible advantage of SAR, as opposed to passive Electro-Optical (EO) sensors, is that weather events do not obscure coverage. SAR imagery can be taken at any time of year, day or night, irrespective of weather conditions. This allows for a consistent flow of imagery to aid in vessel detect. <a href="https://iuu.xview.us/">xView3</a> has used the recent uptick in free, high-quality SAR imagery to generate an open source, large-scale dataset for maritime detection.

The objective of this tutorial is to train a convolutional neural network (CNN) to detect 'dark' fishing vessels operating outside the law It will be broken up into 5 parts:
1. Data Collection
2. Data Processing
3. Model Selection
4. Exploratory Data Analysis
5. Conclusion and Way Forward
"""

# Import required libraries
import os
import csv
import gdal
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from osgeo import ogr
from keras.api._v2.keras import datasets, layers, models, Sequential
from keras_preprocessing.image import ImageDataGenerator

"""<hr class="solid">

## Part 1: Data Collection and Curation

To begin, I retrieved the data set from <a href="https://iuu.xview.us/">xView3's</a> website. It is open source and available to all who sign up with the website. From the website I first pulled the 'tiny' dataset which consists of five training scenes and two validation scenes. I used the 'tiny' set as the full dataset is over 500 scenes and requires at least 2TB of disk space. Inside each scene are seven images saved as TIFs. The most important of these are the VH and VV (vertical and horizontal) SAR images. For this project I trained my CNN using the VH imagery as ships are more likely to be in a horizontal position (relative to the satellite sensor) due to East to West trading routes. The other five are ancillary images including bathymetry and wind direction which I did not use. Regarding the training and validation labels, they came as Comma Separated Value (CSV) files that I loaded into a Pandas dataframe.
"""

path = '/content/drive/MyDrive/Colab Notebooks/SAR'
scenes = ['05bc615a9b0e1159t', '72dba3e82f782f67t', '590dd08f71056cacv', '2899cfb18883251bt', 'b1844cde847a3942v', 'cbe4ad26fe73f118t', 'e98ca5aba8849b06t']

# Read the training and validation labels into a dataframe
train_y_df = pd.read_csv(os.path.join(path, 'train.csv'), quoting=csv.QUOTE_NONE, error_bad_lines=False)
val_y_df = pd.read_csv(os.path.join(path, 'validation.csv'), quoting=csv.QUOTE_NONE, error_bad_lines=False)

# Import VH scenes
scene_590dd08f71056cacv = gdal.Open(os.path.join(path, '590dd08f71056cacv/VH_dB.tif'))
scene_b1844cde847a3942v = gdal.Open(os.path.join(path, 'b1844cde847a3942v/VH_dB.tif'))
scene_05bc615a9b0e1159t = gdal.Open(os.path.join(path, '05bc615a9b0e1159t/VH_dB.tif'))
scene_cbe4ad26fe73f118t = gdal.Open(os.path.join(path, 'cbe4ad26fe73f118t/VH_dB.tif'))
scene_e98ca5aba8849b06t = gdal.Open(os.path.join(path, 'e98ca5aba8849b06t/VH_dB.tif'))
scene_72dba3e82f782f67t = gdal.Open(os.path.join(path, '72dba3e82f782f67t/VH_dB.tif'))
scene_2899cfb18883251bt = gdal.Open(os.path.join(path, '2899cfb18883251bt/VH_dB.tif'))

train_scenes_list = [scene_2899cfb18883251bt, scene_72dba3e82f782f67t, scene_e98ca5aba8849b06t, scene_cbe4ad26fe73f118t, scene_05bc615a9b0e1159t]
val_scenes_list = [scene_590dd08f71056cacv, scene_b1844cde847a3942v]

"""<hr class="solid">

## Part 2: Data Preprocessing
Since I am working with the 'tiny' dataset, the first to do was remove the unused scenes from my label dataframes. From there, I made the decision to only focus on the columns with geospatial information and the is_vessel label. The are other columns such as confidence level and is_fishing but I did not work on them in this tutorial. Next, I removed all the rows where is_vessel is NaN which cannot be used in my model. 

Moving to the SAR scenes themselves, I locate each labeled vessel in the scenes and cut a 256x256px tile around the label while making sure to not include any scene that has no data in it (defined as -32768.0 in this dataset). From there I noticed that over 90% of my subscenes were labeled as a vessel which made me realize I have a massive imbalance in classes. To fix this issue, I randomly sample subscenes without a labeled vessel and add them to my training set until I had an equal balance of scenes labeled vessel and no vessel. While adding to the both the training and validation sets, I generated my y values by appending to an array either 0 if is_vessel is False or 1 if is_vessel is True. Finally, I normalize my data to improve the performance of my model.
"""

train_y_df.head()

val_y_df.head()

# Extract labels for only our scenes
train_y_df = train_y_df[train_y_df['scene_id'].isin(scenes)]
val_y_df = val_y_df[val_y_df['scene_id'].isin(scenes)]

# Remove Nan from is_vessel
train_y_df = train_y_df[np.logical_or(train_y_df['is_vessel'] == True, train_y_df['is_vessel'] == False)]
val_y_df = val_y_df[np.logical_or(val_y_df['is_vessel'] == True, val_y_df['is_vessel'] == False)]

# Many more True than false
np.unique(train_y_df['is_vessel'], return_counts=True)

# Save the ids of our scenes
training_scene_ids = train_y_df.scene_id.unique()
validation_scene_ids = val_y_df.scene_id.unique()

print(training_scene_ids)
print(validation_scene_ids)

# As each SAR image only consists of a single band, open it as an array (grayscale) in a dictionary with the scene id as the key
train_scenes = {id : train_scenes_list[i].GetRasterBand(1).ReadAsArray() for i, id in enumerate(training_scene_ids)}
val_scenes = {id : val_scenes_list[i].GetRasterBand(1).ReadAsArray() for i, id in enumerate(validation_scene_ids)}

"""Visualizing the Training Scenes and Validation Scenes (with labels)

![alt](https://drive.google.com/uc?id=1zeTQCMnuIacijHtMGWz9wXIlXRLQOSDC)  ![alt](https://drive.google.com/uc?id=1l0T3wOqxa2RKa09-qp9CrKi3ID-qI5th)

(I am using QGIS to visualize the imagery as displaying it with a library such as matplotlib would crash the .ipybn. The images are too large for the kernel to handle unless your hardware has loads of RAM)
"""

# The arrays that will contain all our training subscenes to feed to the CNN
train_X = []
train_y = []

# Iterate through each scene in the dictionary
for id, scene in train_scenes.items():

    for index, r in train_y_df[train_y_df['scene_id'] == id].iterrows():
        row = r.detect_scene_row
        col = r.detect_scene_column
        label = 1 if r.is_vessel else 0
        subset = scene[row-128:row+128,col-128:col+128]

        if subset.min() != -32768.0:
            train_X.append(subset)
            train_y.append(label)

# Helper function for creating subscenes without labels
def img_contains_label(x, y, id):
    for index, row in train_y_df[train_y_df['scene_id'] == id].iterrows():
        label_row = r.detect_scene_row
        label_col = r.detect_scene_column
        if label_row > x-128 and label_row < x+128 and label_col > y-128 and label_col < y+128:
            # vessel is in image
            return True
    return False

# Number of images to add to balance out the class
num_img_to_add = sum(train_y)-(len(train_y)-sum(train_y))

# The training set is unbalanced, add no vessel subscenes
for id, scene in train_scenes.items():
    
    for i in range(num_img_to_add // len(train_scenes)):
        max_x = len(scene)
        max_y = len(scene[0])

        while True: 
            x = np.random.randint(128, max_x-128)
            y = np.random.randint(128, max_y-128)
            subset = scene[x-128:x+128,y-128:y+128]
           
            if img_contains_label(x, y, id) or subset.min() == -32768.0:
                continue

            train_X.append(subset)
            train_y.append(0)
            break

# Save as numpy arrays for easy of use with Keras
train_X = np.array(train_X)
train_y = np.array(train_y)

# Much better class balance!
np.unique(train_y, return_counts=True)

# Build the validation dataset
val_X = []
val_y = []

for id, scene in val_scenes.items():
    
    for index, r in val_y_df[val_y_df['scene_id'] == id].iterrows():
        row = r.detect_scene_row
        col = r.detect_scene_column
        label = 1 if r.is_vessel else 0
        subset = scene[row-128:row+128,col-128:col+128] # all vessels are centered...bad

        if subset.min() != -32768.0:
            val_X.append(subset)
            val_y.append(label)

val_X = np.array(val_X)
val_y = np.array(val_y)

# The original arrays are very large and no longer need free them from memory
del train_scenes
del val_scenes

# Normalize data
train_X = (train_X - train_X.min()) / (train_X.max() - train_X.min())
val_X = (val_X - val_X.min()) / (val_X.max() - val_X.min())

# Visualize some scenes
plt.figure(figsize=(15,15))
for i in range(25):
    plt.subplot(5,5,i+1)
    plt.imshow(train_X[i*20], interpolation=None, cmap='gray', vmin=np.nanmin(train_X[i*20]), vmax=np.nanmax(train_X[i*20]))
    plt.xticks([])
    plt.yticks([])
    plt.xlabel(train_y[i*20])
    plt.grid(False)
plt.show()

"""Displayed are a few examples of the subscenes that comprise the training data.

<hr class="solid">

## Part 3/4: Model Training and Analysis
(Parts 3 and 4 are broken into two sections. One for each model trained.)
### Model 1: Custom Design

For my first attempt at building an accurate model, I created a relatively simple convolutional neural network. To bolster the amount of data I could feed into the model, I decided to perform data augmentation. This is a technique that slightly modifies the original images through flipping, rotating, or zooming to create new synthetic data. This is important as I have a limited number of scenes in my 'tiny' dataset and I want to feed as much good data as I can into my model.
"""

data_augmentation = Sequential([
  layers.RandomFlip("horizontal_and_vertical"),
  layers.RandomRotation(0.1),
  layers.RandomZoom(height_factor=(0,0.1)),
])

# Original training set
train_X.shape

train_X = np.concatenate((train_X, data_augmentation(train_X).numpy()))
train_y = np.concatenate((train_y, train_y))

# New training set. The size has doubled!
train_X.shape

"""My custom model is mainly comprised of three convolutional, two pooling, and two dense layers. The convolutional layers are the building blocks of this model that apply a filter to create a feature map. The feature map values are then passed through the ReLu activation function. I chose ReLu for my convolutional layers for its speed. The pooling layers then reduce the matrix from the convolutional layer into a smaller matrix. I have several dropout layers in an effort to prevent overfitting. Near the end of the model, I have several fully connected or dense layers. The first one is directly connected to a flatten layer as the dense layer requires input to be 1D. I use sigmoid activation here as it is <a href="https://towardsdatascience.com/how-to-choose-the-right-activation-function-for-neural-networks-3941ff0e6f9c#:~:text=In%20a%20binary%20classifier%2C%20we,with%20one%20node%20per%20class.">shown to improve binary classification results</a>. Finally, I use my last dense layer to classify my features into one of two classes (vessel or no vessel)."""

model = models.Sequential()

model.add(layers.Conv2D(32, (3, 3), activation='relu', input_shape=(256, 256, 1)))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Conv2D(64, (3, 3), activation='relu'))
model.add(layers.MaxPooling2D((2, 2)))
model.add(layers.Dropout(rate=0.2))
model.add(layers.Conv2D(64, (3, 3), activation='relu'))
model.add(layers.Flatten())
model.add(layers.Dense(64, activation='sigmoid',  kernel_regularizer='l2'))
model.add(layers.Dropout(rate=0.1))
model.add(layers.Dense(2))

model.summary()

model.compile(optimizer='adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

history = model.fit(train_X, train_y, epochs=20, shuffle=True, validation_data=(val_X, val_y))

# Evaluate the model on the train data
train_loss, train_acc = model.evaluate(train_X, train_y, verbose=2)
print(f'Train accuracy: {100*train_acc:.2f}%')

# Evaluate the model on the test data
test_loss, test_acc = model.evaluate(val_X, val_y, verbose=2)
print(f'Test accuracy: {100*test_acc:.2f}%')

"""My custom model does not perform well. It achieves extremely high training accuracy but is worse than a coin flip when it comes to the validation data. This is a classic example of overfitting which I attempted to correct through dropout layers and hyperparameter tuning but could not overcome."""

# Plotting loss, accuracy
plt.subplot(1,2,1)
plt.plot(history.history['loss'], label='loss')
plt.plot(history.history['val_loss'], label = 'val_loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.subplot(1,2,2)
plt.plot(history.history['accuracy'], label='accuracy')
plt.plot(history.history['val_accuracy'], label = 'val_accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.ylim([0, 1])
plt.legend()

plt.tight_layout()
plt.show()

"""<a href="https://en.wikipedia.org/wiki/Softmax_function">Softmax</a> is a function that converts a vector of real numbers into a probability distribution. Here I use it to convert my model's predictions into two values, probability that the subscene is not a vessel and the probability that it is a vessel. """

# Predict and use softmax to convert to probability
predictions = model.predict(val_X)

predictions = tf.nn.softmax(predictions).numpy()

"""To demonstrate my model, I pick a random image in my validation dataset and compare its ground truth to my predicted value. I also show the image to visualize what my model choosing to classify."""

index = np.random.randint(0, len(val_X))

plt.figure(figsize=(15,15))
plt.imshow(val_X[index], cmap='gray', vmin=np.nanmin(val_X[index]), vmax=np.nanmax(val_X[index]))
plt.title(f'Correct={val_y[index]}, Predicted={np.argmax(predictions[index])}')

"""### Model 2: EfficientNetV2B0
After poor performance with my custom model, I decided to apply transfer learning to my detection problem. Transfer learning is the act of reusing a previously trained model on a new problem. For my pretrained model I chose <a href="https://arxiv.org/abs/2104.00298"> EfficientNetV2</a> as I wanted a model that my hardware could handle in terms of RAM and training speed. EfficientNetV2 significantly outperforms other models of similar speed when comparing accuracy and was recently developed in 2021. I thought it would be interesting to test a new family of CNNs on a traditionally hard problem such as SAR vessel detection.

At a very broad level, EfficientNetV2 works through an improved progressive learning technique. It begins with very small images and weak regularization but as it moves through the epochs, the model gradually increases the images size and regularization strength. 

![alt](https://drive.google.com/uc?id=1d75Vr9-lNbKR981Uc5rn_hXxS_HjNsWc)

(EfficientNetv2 Example)
"""

base_model = tf.keras.applications.efficientnet_v2.EfficientNetV2B0(input_shape=(256, 256, 3),
                                               include_top=False,
                                               weights='imagenet',
                                               include_preprocessing=False)

"""For our single band SAR imagery to be properly processed by EfficientNet, we need to project it into three bands (RedGreenBlue). To accomplish this, I copy the single band values into three bands. Viewing the shape of the resulting array shows how we projected all our 256x256px images into 3 'bands'."""

# Our single band SAR image must be projected into 3 bands for use in EfficientNet
train_X_RGB = np.repeat(train_X[..., np.newaxis], 3, -1)
print(train_X_RGB.shape)

val_X_RGB = np.repeat(val_X[..., np.newaxis], 3, -1)
print(val_X_RGB.shape)

# Put training data into model to get features
features = base_model.predict(train_X_RGB)
print(features.shape)

# Freeze the base CNN to prevent EfficientNet from updating its weights
base_model.trainable = False

# Generate predictions from the block of features
global_average_layer = tf.keras.layers.GlobalAveragePooling2D()
features_average = global_average_layer(features)
print(features_average.shape)

# We have only two classes, vessel or no vessel so we need to add a classification layer to convert features into one of these 2 classes
prediction_layer = tf.keras.layers.Dense(2)
prediction = prediction_layer(features_average)
print(prediction.shape)

# Build our model based off EfficientNet
inputs = tf.keras.Input(shape=(256, 256, 3))
x = base_model(inputs, training=False)
x = global_average_layer(x)
# x = tf.keras.layers.Dropout(0.3)(x)
outputs = prediction_layer(x)
model_pretrained = tf.keras.Model(inputs, outputs)

model_pretrained.compile(tf.keras.optimizers.Adam(learning_rate=0.0005),
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

model_pretrained.summary()

history = model_pretrained.fit(train_X_RGB, train_y, epochs=20, shuffle=True, validation_data=(val_X_RGB, val_y))

train_loss, train_acc = model_pretrained.evaluate(train_X_RGB, train_y, verbose=2)
print(f'Train accuracy: {100*train_acc:.2f}%')

# Evaluate the model on the test data
test_loss, test_acc = model_pretrained.evaluate(val_X_RGB,  val_y, verbose=2)
print(f'Test accuracy: {100*test_acc:.2f}%')

predictions = model_pretrained.predict(val_X_RGB)

# Convert predictions to probabilities using softmax
# https://en.wikipedia.org/wiki/Softmax_function
predictions = tf.nn.softmax(predictions).numpy()

"""While my transfer learning model outperforms my custom model, it continues to be worse than a coin toss. Even with dropout layers, overfitting rears its head again as my model's training loss decreases but it's validation loss skyrockets."""

# Plotting loss, accuracy
plt.subplot(1,2,1)
plt.plot(history.history['loss'], label='loss')
plt.plot(history.history['val_loss'], label = 'val_loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

plt.subplot(1,2,2)
plt.plot(history.history['accuracy'], label='accuracy')
plt.plot(history.history['val_accuracy'], label = 'val_accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.ylim([0, 1])
plt.legend()

plt.tight_layout()
plt.show()

"""I again wanted to visualize my model's predictions. It is interesting to view what is predicted correctly and incorrectly. From visualization it seems that my model works well on larger ships but when the ships occupy only a few pixels it has trouble distinguishing them from the pixels of the ocean. Another interesting observation is that my model does well in distinguishing small islands from vessels, something I would not have thought it could do with its low accuracy."""

# Visualize some predictions
plt.figure(figsize=(20,20))
for i in range(25):
    index = np.random.randint(0, len(val_X))
    plt.subplot(5,5,i+1)
    plt.imshow(val_X[index], cmap='gray', vmin=np.nanmin(val_X[index]), vmax=np.nanmax(val_X[index]))
    plt.xticks([])
    plt.yticks([])
    plt.title(f'Correct={val_y[index]}, Predicted={np.argmax(predictions[index])}')
    plt.grid(False)
plt.show()

"""<hr class="solid">

## Part 5:
## Conclusion
In the end, while my results leave much to be desired, I feel that I learned a significant amount about SAR, convolutional neural networks, and data processing. SAR imagery is notoriously difficult to handle but I am happy to have made functioning models. The data science pipeline for training neural networks differs slightly from other Machine Learning techniques and I had to adapt to these differences. Instead of tinkering with many different ML models, training a CNN involves devoting yourself to trying many different iterations of the same model. Tuning hyperparameters, mixing up layers, and researching successful CNNs is a time-consuming task that requires a high level of technical expertise and background knowledge. The ability to develop powerful networks such as EfficientNet is extremely impressive and I am glad to have conducted the research. 
## Way Forward
Moving forward, I have several ideas on how to improve my model???s accuracy. First, I completely neglected the VV SAR scenes. While vertical data is not as important for ship detection as horizontal, the scenes likely still contain information relevant to my models. What I would do next is create an RGB composite of my VH and VV scenes using GDAL. This composite containing both vertical and horizontal information could then be used to construct the subscenes. Second, there are five auxiliary images that I did not use. While not as important as the VV scenes, they may contain useful learning data that could be implemented into my model???s learning. Third, I decided to go with binary classification for simplicity but in the original labels, the vessels were given a confidence level (Low, Medium, or High). It would be interesting to test my model???s accuracy by having it try to predict four classes. Either not a vessel or one of the confidence levels. There was other data in the labels as well, such as is fishing, but I cannot think of any good uses for this information at this time. Finally, and most optimistically, I would like to try and train my model on the entire dataset. The ???tiny??? dataset is easy to use but represents only a fraction of the available SAR data. With more time and better hardware to perform more epochs on more data it is possible I could have achieved better results. Thank you for following me through this tutorial, I hope you learned something new!

"""