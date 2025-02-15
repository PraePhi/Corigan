# author : Paul Tresson for CIRAD in 2019
# contributor : Dominique Carval


import os
import utils
import time
import pandas
import argparse
from slice import slice_train, slice_test
import slice_PIL
from plot_bbox import plot_bbx
from refine_date import refine_detections
from performances_analysis import get_metrics, get_confusion_matrix
from count_object_per_class import find_all_files
import insects_analysis

# initialize time
t0 = time.time()

###############################                  update options             ############################################

parser = argparse.ArgumentParser()

# general settings

parser.add_argument('--mode', type=str, default='test',
                    help="train or test")
parser.add_argument('--show_plot', type=str, default=False,
                    help="show image with bbx ?")
parser.add_argument('--save_plot', type=str, default=False,
                    help="save image with bbox ?")
parser.add_argument('--dont_slice', type=str, default=False,
                    help="True to skip slicing")
parser.add_argument('--dont_metrics', type=str, default=False,
                    help="True to skip comparison to GT")
parser.add_argument('--dont_use_openCV', type=str, default=False,
                    help="True to use PIL rather than openCV")
parser.add_argument('--train_record', type=str, default=False,
                    help="True to export training info for further analysis")
parser.add_argument('--get_outputs', type=str, default=False,
                    help="True to get ecological outputs")

# set parameters for slicing and refining

parser.add_argument('--slice_width', type=str, default=416,
                    help="slice width in pixels")
parser.add_argument('--slice_overlap', type=str, default=0.2,
                    help="overlap during slicing")
parser.add_argument('--Pobj', type=str, default=0.4,
                    help="minimal proportion of the object in the slice for label recomputing")
parser.add_argument('--Pimage', type=str, default=0.2,
                    help="minimal proportion of the slice covered by an object for label recomputing")
parser.add_argument('--slice_overlap', type=str, default=0.2,
                    help="overlap during slicing")
parser.add_argument('--detection_thr', type=str, default=0.2,
                    help="detection threshold for testing")
parser.add_argument('--overlap_thr', type=str, default=0.4,
                    help="overlap threshold for testing")

# set parameters for model training and testing

parser.add_argument('--classes', type=str, default='simple',
                    help="simple or detailed")
# we have been working with simple and detailled classes. If such a distinction is not useful, you can remove it.
# this is used for .cfg file and .names file (cf. 'update directories' below).

parser.add_argument('--weights_file', type=str, default='yolov3-simple_44100.weights',
                    help="weights file name")

args = parser.parse_args()

mode = args.mode
show_plot = args.show_plot
save_plot = args.save_plot
dont_perform_slicing = args.dont_slice
dont_perform_metrics = args.dont_metrics
dont_use_openCV = args.dont_use_openCV
train_record = args.train_record
get_outputs = args.get_outputs

slice_width = args.slice_width
slice_overlap = args.slice_overlap
Pobj = args.Pobj
Pimage = args.Pimage
dt_thr = args.detection_thr
ov_thr = args.overlap_thr

classes_mode = args.classes  # comment if not working with different classes labelling
weights_file = args.weights_file


####################################               update directories                  #################################

core_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_dir = os.path.dirname(core_dir)
print(pipeline_dir)

train_im_dir = os.path.join(pipeline_dir, 'train_images')
test_im_dir = os.path.join(pipeline_dir, 'test_images')

# list all test images
test_images_list = [f for f in os.listdir(test_im_dir) if (f.endswith('.jpg') or f.endswith('.JPG'))]
train_tmp_dir = os.path.join(pipeline_dir, 'train_temp')
test_tmp_dir = os.path.join(pipeline_dir, 'test_temp')
results_dir = os.path.join(pipeline_dir, 'results')
cfg_dir = os.path.join(pipeline_dir, 'cfg')

train_slice_dir = os.path.join(train_tmp_dir, 'slice')
if not os.path.isdir(train_slice_dir):  # ensures that a 'slice' directory exists
    os.makedirs(train_slice_dir)
test_slice_dir = os.path.join(test_tmp_dir, 'slice')
if not os.path.isdir(test_slice_dir):  # ensures that a 'slice' directory exists
    os.makedirs(test_slice_dir)
name_file_dir = train_tmp_dir

# included by Dom

# data_file_path = os.path.join(cfg_dir, 'classes.txt')
saved_data_file_path = os.path.join(train_tmp_dir, 'training_examples_per_class.csv')

# end of included by Dom

# update cfg file
cfg_file = 'yolov3-' + classes_mode + '.cfg'  # change if working with different cfg file
cfg_file_path_short = 'cfg/' + cfg_file

# update weights and pre-trained layers
weights_file_path_short = 'train_temp/backup/' + weights_file
# pre_trained_layers = 'cfg/darknet53.conv.74' # recommended for first training
pre_trained_layers = 'train_temp/backup/yolov3-detailed_433_images_last.weights'


# update name file
name_file = 'insects_' + classes_mode + '.names'  # change if working with different name file
name_file_tot = os.path.join(cfg_dir, name_file)
name_file_short = 'cfg/' + name_file

num_classes = sum(1 for line in open(name_file_tot))  # will be needed for darknet and is always good to check
print('number of classes : ' + str(num_classes))

#
#
#
#
#

# now that everything is checked, the real use of the pipeline begins.

########################################################################################################################
##                                                     TRAIN                                                          ##
########################################################################################################################

if mode == 'train':

    print('\ntrain\n')

    # included by Dom
    # To calculate the number of training examples per class
    find_all_files(train_im_dir, name_file_tot, saved_data_file_path)
    # end of included by Dom

    ########################################## slicing ################################################

    if not dont_perform_slicing:  # if slicing were already done previously, you might want to skip it

        utils.clean_dir(train_slice_dir)
        print('slicing files ...')

        # openCV can be heavier to use depending on your setup, you have the option to use PIL instead

        if not dont_use_openCV:
            slice_train(train_im_dir, train_slice_dir, sliceWidth=slice_width, sliceHeight=slice_width,
                        overlap=slice_overlap, Pobj=Pobj, Pimage=Pimage)
        else:
            slice_PIL.slice_train(train_im_dir, train_slice_dir, sliceWidth=slice_width, sliceHeight=slice_width,
                                  overlap=slice_overlap, Pobj=Pobj, Pimage=Pimage)

        if not dont_use_openCV:
            utils.list_files(train_slice_dir, '.png', train_tmp_dir, 'train')  # slices are listed to be used by darknet
        else:
            utils.list_files(train_slice_dir, '.jpg', train_tmp_dir, 'train')

        t1 = time.time()
        print('\nLength of time to slice files: ' + str(t1 - t0) + ' seconds\n')

    train_list_file = os.path.join(train_tmp_dir, 'train.txt')

    ###################################### edit command line #######################################

    # edit data file needed for darknet
    # this file tell darknet where to get the different data or information

    data_file_path = os.path.join(cfg_dir, 'train.data')
    data_file = open(data_file_path, 'w')
    data_file.write('classes= %d\n' % num_classes)
    data_file.write('train= %s\n' % train_list_file)
    data_file.write('names= %s\n' % (name_file_tot,))
    data_file.write('backup = %s/backup\n' % train_tmp_dir)  # where the weights files will be stored
    data_file.close()
    data_file_path_short = 'cfg/train.data'

    # edit command line
    if not train_record:
        cmd = './darknet detector train ' + data_file_path_short + ' ' + cfg_file_path_short + ' ' + pre_trained_layers + ''
    else:
        cmd = './darknet detector train ' + data_file_path_short + ' ' + cfg_file_path_short + ' ' + pre_trained_layers + '>> train_record_433.log'
    print(cmd)

    ######################################## execute command ###########################################
    os.system(cmd)

    t2 = time.time()
    train_duration = (t2 - t0) / 3600
    print('\nLength of time to train: ' + str(train_duration) + ' hours\n')

#
#
#
# test and use mode are basically the same.
# For use mode, you just do not need to perform performance analysis (i.e. set --dont_metrics=True)

########################################################################################################################
##                                                     TEST                                                           ##
########################################################################################################################

if mode == 'test':

    print('\ntest\n')

    # included by Dom
    # To calculate the number of training examples per class
    find_all_files(train_im_dir, name_file_tot, saved_data_file_path)
    # end of included by Dom

    ########################################## slicing ################################################
    # slicing. Again, you can choose how you want to perform it
    if not dont_perform_slicing:

        utils.clean_dir(test_slice_dir)
        print('slicing files ...')

        if not dont_use_openCV:
            slice_test(test_im_dir, test_slice_dir, sliceWidth=slice_width, sliceHeight=slice_width, overlap=slice_overlap)
        else:
            slice_PIL.slice_test(test_im_dir, test_slice_dir, sliceWidth=slice_width, sliceHeight=slice_width, overlap=slice_overlap)

        t1 = time.time()
        print('\nLength of time to slice: ' + str(t1 - t0) + ' seconds\n')

    if not dont_use_openCV:
        utils.list_files(test_slice_dir, '.png', test_tmp_dir, 'test')
    else:
        utils.list_files(test_slice_dir, '.jpg', test_tmp_dir, 'test')

    test_list_file_short = 'test_temp/test.txt'

    ###################################### edit command line #######################################

    result_file_short = 'test_temp/result.txt'
    data_file_path_short = 'cfg/train.data'
    # this makes the assumption that you perform test after train but you might want to check the train.data file

    ######################################## execute command ###########################################

    cmd = './darknet detector test ' + data_file_path_short + ' ' + cfg_file_path_short + ' ' + weights_file_path_short + ' -dont_show -ext_output < ' + test_list_file_short + ' > ' + result_file_short + ''
    print(cmd)
    os.system(cmd)

    ##################################### refine detections ############################################

    refine_detections(result_file_short, detection_threshold=float(dt_thr), overlap_threshold=float(ov_thr),test_im_dir=test_im_dir)

    detection_df = pandas.read_csv('test_temp/refined_detections.csv')

    ################################### comparison with ground truth ##################################

    # if you only want to perform detection and not test, you might want to skip it
    if not dont_perform_metrics:
        # compare with ground truth
        get_metrics(test_im_dir, 'test_temp/refined_detections.csv', name_file_short, saved_data_file_path)
        print('\nediting confusion matrix in test_temp directory...')
        # included by Dom
        #complete_metrics_per_class('test_temp/general_metrics.csv', saved_data_file_path)

        # end of included by Dom

        get_confusion_matrix(test_im_dir, 'test_temp/refined_detections.csv', name_file_short)
        print('[done]')

    else:
        pass

    t2 = time.time()
    print('\nLength of time to test (slice + detection): ' + str(t2 - t0) + ' seconds')
    print('(= ' + str((t2 - t0) / 60) + ' min)')

    # plot detections ?
    if show_plot:
        for image in test_images_list:
            image_path = os.path.join(test_im_dir, image)
            plot_bbx(image_path, detection_df)

    if save_plot:

        if not os.path.isdir("test_temp/plot"):  # ensures that a 'plot' directory exists
            os.makedirs("test_temp/plot")

        for image in test_images_list:
            image_path = os.path.join(test_im_dir, image)
            image_name = image.split('.')[0]
            outname = 'test_temp/plot/' + image_name + '_plot.jpg'
            plot_bbx(image_path, detection_df, show=False, save=True, outname=outname)


##########################################     ecological outputs   ####################################################

    if get_outputs:

        print('\n###  computing ecological outputs  ####\n')

        print('species count...')
        insects_analysis.count_species_detection('test_temp/refined_detections.csv', print_res=False, edit_res=True)
        insects_analysis.count_species_gt(test_im_dir, name_file_short, print_res=False, edit_res=True)

        print('interactions ...')
        insects_analysis.count_interactions_detection('test_temp/refined_detections.csv', print_res=False, edit_res=True)
        insects_analysis.count_inter_gt(test_im_dir, name_file_short, print_res=False, edit_res=True)

        print('intra-specific interactions count...')
        insects_analysis.count_intra_detection('test_temp/refined_detections.csv', print_res=False, edit_res=True)
        insects_analysis.count_intra_gt(test_im_dir, name_file_short, print_res=False, edit_res=True)

        print('interactions analysis...')
        insects_analysis.interaction_analysis()
        insects_analysis.predation_statistics('test_temp/refined_detections.csv')

        print('interactions for network visualisation...')
        insects_analysis.reformat_interaction_file()

        print('[done]')

