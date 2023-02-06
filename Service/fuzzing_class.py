from __future__ import print_function

from keras.layers import Input
from scipy.misc import imsave
from utils_tmp import init_coverage_times,init_coverage_value
import sys
import os
import time
from multiprocessing import Process,Queue

class DLFuzzClass():
    def __init__(self, shape, filePath, codeFileName, loadModelFunctionName):
        self.input_tensor = Input(shape=shape)
        codeFileName="model_save.luojiale_241493798414."+codeFileName
        print(codeFileName)
        module = __import__(codeFileName,fromlist=(filePath,))
        modelFunction = getattr(module,loadModelFunctionName)
        self.model = modelFunction(input_tensor=self.input_tensor)
        print(filePath)
        self.model.load_weights(filePath+'/Model1.h5')
        if self.model:
            print("Model loading success")
            self.ModelLoadingFlag = True
        else:
            print("Model loading fail")
            self.ModelLoadingFlag = False
        
    def fuzzing_init(self,imgPath, neuron_select_strategy, threshold, neuron_to_cover_num, subdir, iteration_times):
        self.model_layer_times1 = init_coverage_times(self.model)  # times of each neuron covered
        self.model_layer_times2 = init_coverage_times(self.model)  # update when new image and adversarial images found
        self.model_layer_value1 = init_coverage_value(self.model)


        self.img_dir = imgPath
        self.img_paths = os.listdir(self.img_dir)
        self.img_num = len(self.img_paths)


        self.neuron_select_strategy = neuron_select_strategy
        self.threshold = float(threshold)
        self.neuron_to_cover_num = int(neuron_to_cover_num)
        self.save_dir = subdir +'/'
        self.iteration_times = int(iteration_times)
        self.neuron_to_cover_weight = 0.5
        self.predict_weight = 0.5
        self.learning_step = 0.02
        if os.path.exists(self.save_dir):
            for i in os.listdir(self.save_dir):
                path_file = os.path.join(self.save_dir, i)
                if os.path.isfile(path_file):
                    os.remove(path_file)

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)


        self.total_time = 0
        self.total_norm = 0
        self.adversial_num = 0
        self.total_perturb_adversial = 0

    def fuzzing_run(self,ID,q,layer_name):
        for i in range(self.img_num):
            start_time = time.clock()
            img_list = []
            img_path = os.path.join(self.img_dir,self.img_paths[i])
            img_name = self.img_paths[i].split('.')[0]
            mannual_label = int(img_name.split('_')[1])
            # print(img_path,ID)
            tmp_img = preprocess_image(img_path)
            orig_img = tmp_img.copy()
            img_list.append(tmp_img)
            # print(img_path,ID)
            update_coverage(tmp_img, self.model, self.model_layer_times2, self.threshold)
            while len(img_list) > 0:
                gen_img = img_list[0]
                img_list.remove(gen_img)
                # first check if input already induces differences
                pred1 = self.model.predict(gen_img)
                label1 = np.argmax(pred1[0])
                label_top5 = np.argsort(pred1[0])[-5:]
                update_coverage_value(gen_img, self.model, self.model_layer_value1)
                update_coverage(gen_img, self.model, self.model_layer_times1, self.threshold)
                orig_label = label1
                orig_pred = pred1
                loss_1 = K.mean(self.model.get_layer(layer_name).output[..., orig_label])
                loss_2 = K.mean(self.model.get_layer(layer_name).output[..., label_top5[-2]])
                loss_3 = K.mean(self.model.get_layer(layer_name).output[..., label_top5[-3]])
                loss_4 = K.mean(self.model.get_layer(layer_name).output[..., label_top5[-4]])
                loss_5 = K.mean(self.model.get_layer(layer_name).output[..., label_top5[-5]])
                layer_output = (self.predict_weight * (loss_2 + loss_3 + loss_4 + loss_5) - loss_1)
                # neuron coverage loss
                loss_neuron = neuron_selection(self.model, self.model_layer_times1, self.model_layer_value1, self.neuron_select_strategy,
                                            self.neuron_to_cover_num, self.threshold)
                # loss_neuron = neuron_scale(loss_neuron) # useless, and negative result
                # extreme value means the activation value for a neuron can be as high as possible ...
                EXTREME_VALUE = False
                if EXTREME_VALUE:
                    self.neuron_to_cover_weight = 2
                layer_output += self.neuron_to_cover_weight * K.sum(loss_neuron)
                # for adversarial image generation
                final_loss = K.mean(layer_output)
                # we compute the gradient of the input picture wrt this loss
                grads = normalize(K.gradients(final_loss, self.input_tensor)[0])
                grads_tensor_list = [loss_1, loss_2, loss_3, loss_4, loss_5]
                grads_tensor_list.extend(loss_neuron)
                grads_tensor_list.append(grads)
                # this function returns the loss and grads given the input picture
                iterate = K.function([self.input_tensor], grads_tensor_list)
                # we run gradient ascent for 3 steps
                for iters in range(self.iteration_times):
                    loss_neuron_list = iterate([gen_img])
                    perturb = loss_neuron_list[-1] * self.learning_step
                    gen_img += perturb
                    # previous accumulated neuron coverage
                    previous_coverage = neuron_covered(self.model_layer_times1)[2]
                    pred1 = self.model.predict(gen_img)
                    label1 = np.argmax(pred1[0])
                    update_coverage(gen_img, self.model, self.model_layer_times1, self.threshold) # for seed selection
                    current_coverage = neuron_covered(self.model_layer_times1)[2]
                    diff_img = gen_img - orig_img
                    L2_norm = np.linalg.norm(diff_img)
                    orig_L2_norm = np.linalg.norm(orig_img)
                    perturb_adversial = L2_norm / orig_L2_norm
                    if current_coverage - previous_coverage > 0.01 / (i + 1) and perturb_adversial < 0.02:
                        img_list.append(gen_img)
                        # print('coverage diff = ', current_coverage - previous_coverage, 'perturb_adversial = ', perturb_adversial)
                    if label1 != orig_label:
                        update_coverage(gen_img, self.model, self.model_layer_times2, self.threshold)
                        self.total_norm += L2_norm
                        self.total_perturb_adversial += perturb_adversial
                        # print('L2 norm : ' + str(L2_norm))
                        # print('ratio perturb = ', perturb_adversial)
                        gen_img_tmp = gen_img.copy()
                        gen_img_deprocessed = deprocess_image(gen_img_tmp)
                        save_img = self.save_dir + img_name + '_' + str(get_signature()) + '.png'
                        imsave(save_img, gen_img_deprocessed)
                        self.adversial_num += 1
            # q.put('4')
            end_time = time.clock()
            # print('covered neurons percentage %d neurons %.3f'
                # % (len(self.model_layer_times2), neuron_covered(self.model_layer_times2)[2]))
            duration = end_time - start_time
            # print('used time : ' + str(duration))
            self.total_time += duration
            if q.qsize() == 1:
                q.get()
            q.put({
                "ID":ID,
                "image path":img_path,
                "covered neurons percentage":len(self.model_layer_times2),
                "neurons":neuron_covered(self.model_layer_times2)[2],
                "FLAG":False
            })
        q.put({"FLAG":True})
            
    
def createModule(shape,codeFileName,loadModelFunctionName,seedPath,neuron_select_strategy,threshold,neuron_to_cover_num,subdir,iteration_times,ID,q,layer_name):
    item = DLFuzzClass(shape,codeFileName,loadModelFunctionName)
    item.fuzzing_init(seedPath,neuron_select_strategy,threshold,neuron_to_cover_num,subdir,iteration_times)
    item.fuzzing_run(ID,q,layer_name)


if __name__ == "__main__":
    print("Testing .......")








