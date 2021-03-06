import os
import gen
import aug
import loader
import hangul

import tensorflow as tf
import numpy as np
import cv2 as cv
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
from datetime import datetime

INPUT_SHAPE = (74, 74, 3)

LEARNING_RATE = 0.0005
BATCH_SIZE = 64

LAYER_1_1_NEURON_COUNT = 512
LAYER_2_1_NEURON_COUNT = 512
LAYER_3_1_NEURON_COUNT = 512
LAYER_4_1_NEURON_COUNT = 512

EPOCH_COUNT = 1
TEST_RATE = 0.05
LOAD_FROM_NPY = False
LOAD_FROM_CREATED = False
CREATE_DATA = False
SHUFFLE_DATA = False
AUGMENTATION = True
BACKBONE_TRAINING = True
HANGUL_MODEL_TRAINING = True
ASCII_MODEL_TRAINING = False

PREDICTION = True
TRAINING = True


class CustomGenerator(tf.keras.utils.Sequence):
    def __init__(self, file_list, label_number, batch_size, class_count, augmentation=None):
        self.file_list = file_list
        self.label_number = label_number
        self.batch_size = batch_size
        self.class_count = class_count
        self.augmentation = augmentation

        self.avg1 = 0
        self.avg2 = 0
        self.first = 0
        self.last = 0
        self.cnt = 0

    def __len__(self):
        return (np.ceil(len(self.file_list) / float(self.batch_size))).astype(np.int)

    def __getitem__(self, idx):
        batch_x = self.get_batch_x(idx)
        batch_y, k = self.get_batch_y(idx)

        return batch_x, batch_y

    def get_batch_x(self, idx):
        # set batch_x
        file_list = self.file_list[idx * self.batch_size: (idx + 1) * self.batch_size]

        image_list = [cv.imread(file_name) for file_name in file_list]
        for i in range(0, len(image_list)):
            image = image_list[i]
            image = cv.resize(image, dsize=(INPUT_SHAPE[0], INPUT_SHAPE[1]), interpolation=cv.INTER_CUBIC)
            if self.augmentation is not None:
                image = self.augmentation.randomize(image, INPUT_SHAPE[0], INPUT_SHAPE[1])
            image_list[i] = image

        batch_x = np.array(image_list) / 255

        return batch_x

    def get_batch_y(self, idx):
        # set batch_y
        label_number = self.label_number[idx * self.batch_size: (idx + 1) * self.batch_size]

        size = label_number.shape[0]
        y1 = np.zeros((size, self.class_count[0]))
        y2 = np.zeros((size, self.class_count[1]))
        y3 = np.zeros((size, self.class_count[2]))
        y4 = np.zeros((size, self.class_count[3]))

        for i in range(0, size):
            if label_number[i] < hangul.HANGUL_COUNT:
                onset_number, nucleus_number, coda_number = hangul.hangul_decode_by_number(label_number[i])

                y1[i] = tf.keras.utils.to_categorical(0, self.class_count[0])
                y2[i] = tf.keras.utils.to_categorical(onset_number + 1, self.class_count[1])
                y3[i] = tf.keras.utils.to_categorical(coda_number, self.class_count[2])
                y4[i] = tf.keras.utils.to_categorical(nucleus_number + 1, self.class_count[3])

            else:
                ascii_number = label_number[i] - hangul.HANGUL_COUNT + 1

                y1[i] = tf.keras.utils.to_categorical(ascii_number, self.class_count[0])
                y2[i] = tf.keras.utils.to_categorical(0, self.class_count[1])
                y3[i] = tf.keras.utils.to_categorical(0, self.class_count[2])
                y4[i] = tf.keras.utils.to_categorical(0, self.class_count[3])

        batch_y = (y1, y2, y3, y4)
        return batch_y, label_number


def main():
    # directory
    current_dir = os.path.abspath("")
    font_dir = os.path.join(current_dir, 'font')
    checkpoint_dir = os.path.join(current_dir, 'hangul_OCR_training')
    model_dir = os.path.join(current_dir, 'model')
    data_dir = "G:\hangul_OCR"

    # get generate class
    cg = gen.CharacterGenerator()
    tg = gen.TextImageGenerator(font_dir)
    character_count = cg.get_character_count()

    # ----- train/test data -----

    # set data path
    etri_data_path = os.path.join(data_dir, "syllable")
    etri_json_path = os.path.join(data_dir, "printed_data_info.json")
    # hw_data_path = os.path.join(data_dir, "hand_written_syllable")
    # hw_json_path = os.path.join(data_dir, "handwriting_data_info1.json")
    created_data_path = os.path.join(data_dir, "created")

    # create data
    if CREATE_DATA:
        loader.create_data(cg, tg, font_dir, created_data_path)

    if LOAD_FROM_NPY:
        x_train_file_list = np.load('x_train_file_list.npy')
        y_train = np.load('y_train.npy')
        x_test_file_list = np.load('x_test_file_list.npy')
        y_test = np.load('y_test.npy')

    elif LOAD_FROM_CREATED:
        file_list, label_number = loader.created_data_loader(created_data_path, cg)
        label_number = np.array(label_number, dtype=np.int)
        file_list_shuffled, label_shuffled = shuffle(file_list, label_number)
        x_train_file_list, x_test_file_list, y_train, y_test = \
            train_test_split(file_list_shuffled, label_shuffled,
                             test_size=TEST_RATE, random_state=1)

    else:
        # load data
        file_list, label_number = loader.data_loader(cg, created_data_path, etri_data_path, etri_json_path)
        # file_list, label_number = loader.hand_written_data_loader(cg, hw_data_path, hw_json_path)

        # split data
        file_list_shuffled, label_shuffled = shuffle(file_list, label_number)
        x_train_file_list, x_test_file_list, y_train, y_test = \
            train_test_split(file_list_shuffled, label_shuffled,
                             test_size=TEST_RATE, random_state=1)

        np.save('x_train_file_list.npy', x_train_file_list)
        np.save('y_train.npy', y_train)

        np.save('x_test_file_list.npy', x_test_file_list)
        np.save('y_test.npy', y_test)

    if SHUFFLE_DATA:
        x_train_file_list, y_train = shuffle(x_train_file_list, y_train)
        x_test_file_list, y_test = shuffle(x_test_file_list, y_test)

    # ----- set generator -----

    # image augmentation
    if not AUGMENTATION:
        augmentation = None
    else:
        augmentation = aug.AugmentationGenerator()
        augmentation.ORIGINAL_RATE = 0.2
        augmentation.SHEARING_PROBABILITY = 0.3
        augmentation.RANDOM_MORPHOLOGICAL_TRANSFORM_PROBABILITY = 0.0
        augmentation.NOISING_PROBABILITY = 0.3

    # custom generator
    training_batch_generator = CustomGenerator(x_train_file_list, y_train,
                                               batch_size=BATCH_SIZE, augmentation=augmentation,
                                               class_count=[character_count - hangul.HANGUL_COUNT + 1,
                                                            hangul.ONSET_COUNT + 1, hangul.CODA_COUNT,
                                                            hangul.NUCLEUS_COUNT + 1])

    test_batch_generator = CustomGenerator(x_test_file_list, y_test,
                                           batch_size=BATCH_SIZE, augmentation=None,
                                           class_count=[character_count - hangul.HANGUL_COUNT + 1,
                                                        hangul.ONSET_COUNT + 1, hangul.CODA_COUNT,
                                                        hangul.NUCLEUS_COUNT + 1])

    # ----- model design -----

    # set Mobilenet backbone model
    input_layer = tf.keras.layers.Input(shape=INPUT_SHAPE)
    backbone_model = tf.keras.applications.DenseNet201(
        weights='imagenet', input_shape=INPUT_SHAPE, input_tensor=input_layer, include_top=False, pooling='avg')
    backbone_output = backbone_model.output

    # set output layer
    # with CC (Classifier Chain)
    chain_layer = backbone_output
    x = chain_layer
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(LAYER_1_1_NEURON_COUNT, activation='relu')(x)
    onset_layer = tf.keras.layers.Dense(hangul.ONSET_COUNT + 1, activation='softmax', name='onset_output')(x)

    chain_layer = tf.keras.layers.concatenate([chain_layer, onset_layer])
    x = chain_layer
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(LAYER_2_1_NEURON_COUNT, activation='relu')(x)
    coda_layer = tf.keras.layers.Dense(hangul.CODA_COUNT, activation='softmax', name='coda_output')(x)

    chain_layer = tf.keras.layers.concatenate([chain_layer, coda_layer])
    x = chain_layer
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(LAYER_3_1_NEURON_COUNT, activation='relu')(x)

    nucleus_layer = tf.keras.layers.Dense(hangul.NUCLEUS_COUNT + 1,
                                          activation='softmax', name='nucleus_output')(x)

    x = backbone_output
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Dense(LAYER_4_1_NEURON_COUNT, activation='relu')(x)
    ascii_layer = tf.keras.layers.Dense(character_count - hangul.HANGUL_COUNT + 1,
                                        activation='softmax', name='ascii_output')(x)

    # set training model
    hangul_model = tf.keras.Model(
        inputs=[input_layer],
        outputs=[onset_layer, coda_layer, nucleus_layer]
    )
    hangul_model.trainable = HANGUL_MODEL_TRAINING

    ascii_model = tf.keras.Model(
        inputs=[input_layer],
        outputs=[ascii_layer]
    )
    ascii_model.trainable = ASCII_MODEL_TRAINING

    backbone_model.trainable = BACKBONE_TRAINING
    model = tf.keras.Model(
        inputs=[input_layer],
        outputs=[ascii_model.output] + hangul_model.output
    )

    # model.summary()
    # tf.keras.utils.plot_model(model, "model.png", show_shapes=False)

    # load latest trained weight
    latest_weight = tf.train.latest_checkpoint(checkpoint_dir)
    if latest_weight is not None:
        print("##### weight loaded successfully")
        print(latest_weight)
        model.load_weights(latest_weight)

    # create tensorboard callback
    # command: tensorboard --logdir logs
    log_dir = os.path.join(current_dir, "logs")
    log_dir = os.path.join(log_dir, datetime.now().strftime("%Y%m%d-%H%M%S"))
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, update_freq=1000)

    # create checkpoint callback
    checkpoint_path = os.path.join(checkpoint_dir, "cp-{epoch:04d}.ckpt")
    checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        checkpoint_path, verbose=1, save_weights_only=True)

    # loss weights
    ascii_weights = 1.0 if ASCII_MODEL_TRAINING else 0.0
    hangul_weights = 1.0 if HANGUL_MODEL_TRAINING else 0.0
    loss_weights = [ascii_weights] + ([hangul_weights] * 3)

    # compile model
    optimizer = tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE, decay=0.00005)
    model.compile(optimizer=optimizer,
                  loss={
                      "ascii_output": tf.keras.losses.CategoricalCrossentropy(),
                      "onset_output": tf.keras.losses.CategoricalCrossentropy(),
                      "coda_output": tf.keras.losses.CategoricalCrossentropy(),
                      "nucleus_output": tf.keras.losses.CategoricalCrossentropy()
                  },
                  metrics=['accuracy'], loss_weights=loss_weights)

    # ----- training -----

    # training
    if TRAINING:
        model.fit(training_batch_generator,
                  epochs=EPOCH_COUNT,
                  callbacks=[tensorboard_callback, checkpoint_callback],
                  validation_data=test_batch_generator, shuffle=True)

        # save model
        model_path = os.path.join(model_dir, 'hangul_OCR_model.h5')
        model.save(model_path)
        print("training complete")

    # ----- prediction -----

    # prediction
    if PREDICTION:
        test_images = np.load("test_x.npy", allow_pickle=True)
        test_labels = np.load("test_y.npy", allow_pickle=True)
        test_size = test_images.shape[0]

        resized_images = np.zeros((test_size, INPUT_SHAPE[0], INPUT_SHAPE[1], INPUT_SHAPE[2]), dtype=np.float64)
        for i in range(0, test_size):
            image = cv.resize(test_images[i], dsize=(INPUT_SHAPE[0], INPUT_SHAPE[1]), interpolation=cv.INTER_CUBIC)
            image = aug.to_binary_image(image)
            image = aug.to_output_image(image)
            resized_images[i] = image
        input_x = resized_images / 255

        output = model.predict(input_x)
        y1 = output[0]
        y2 = output[1]
        y3 = output[2]
        y4 = output[3]

        total_count = 0
        hit_count = 0

        for i in range(0, y1.shape[0]):
            if test_labels[i] == "-":
                continue
            total_count = total_count + 1

            ascii_number = y1[i].argmax()
            onset_number = y2[i].argmax()
            coda_number = y3[i].argmax()
            nucleus_number = y4[i].argmax()

            ascii_number = 0
            if ascii_number != 0:
                # ascii character
                char_number = ascii_number + hangul.HANGUL_COUNT
                accuracy = y1[i][ascii_number]

            elif onset_number == 0 or nucleus_number == 0:
                # no character
                char_number = -1
                accuracy = y1[i][ascii_number] * y2[i][onset_number] * y3[i][coda_number] * y4[i][nucleus_number]

            else:
                # hangul character
                char_number = hangul.hangul_encode_to_number(onset_number - 1, nucleus_number - 1, coda_number)
                accuracy = y2[i][onset_number] * y3[i][coda_number] * y4[i][nucleus_number]

            if char_number != -1:
                char = cg.number_to_char(char_number)
            else:
                char = None

            print(f"Label:{test_labels[i]}, Predict:{char}, accuracy:{round(accuracy * 100, 2)}")

            if char == test_labels[i]:
                hit_count = hit_count + 1
            else:
                pass
                """
                cv.imshow("hi", resized_images[i])
                k = cv.waitKey()
                if k == ord("c"):
                    cv.imwrite("k.jpg", resized_images[i])
                """

        print(f"total_count: {total_count}")
        print(f"hit_count: {hit_count}")
        print(f"accuracy: {hit_count/total_count}")


if __name__ == '__main__':
    main()
