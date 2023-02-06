from flask import Flask, request
from fuzzing_class import DLFuzzClass
import subprocess
from multiprocessing import Process,Queue
import os
from utils_tmp import get_signature
import zipfile
 
# # 将目录的文件复制到指定目录
# def copy_demo(src_dir, dst_dir):
#     if not os.path.exists(dst_dir):
#         os.makedirs(dst_dir)
#     if os.path.exists(src_dir):
#         for file in os.listdir(src_dir):
#             file_path = os.path.join(src_dir, file)
#             dst_path = os.path.join(dst_dir, file)
#             if os.path.isfile(os.path.join(src_dir, file)):
#                 copyfile(file_path, dst_path)
#             else:
#                 copy_demo(file_path, dst_path)


app = Flask(__name__)

q_list = {}

        
def createModule(shape,filePath,codeFileName,loadModelFunctionName,seedPath,neuron_select_strategy,threshold,neuron_to_cover_num,subdir,iteration_times,ID,q,layer_name):
    item = DLFuzzClass(shape,filePath,codeFileName,loadModelFunctionName)
    item.fuzzing_init(seedPath,neuron_select_strategy,threshold,neuron_to_cover_num,subdir,iteration_times)
    item.fuzzing_run(ID,q,layer_name)

@app.route('/', methods=['GET','POST'])
def get_argv():
    if request.method == 'POST':
        # python gen_diff.py [2] 0.5 5 0602 5 model1
        neuron_select_strategy = request.form['strategy']  # [2]
        threshold = float(request.form['threshold'])  # 0.5
        neuron_to_cover_num = int(request.form['neuron_to_cover_num'])  # 5
        iteration_times = int(request.form['iteration_times'])  # 5
        ID = request.form['ID']  # 1
        shape = tuple(eval(request.form['shape']))
        load_module_function_name = request.form['load_module_function_name']
        layer_name = request.form['layer_name']
        q_list[ID] = Queue(5)
        
        code_F = request.files['codeFile']
        model_F = request.files['modelFile']
        seed_F = request.files['seed']

        
        file_path = "./model_save/" + ID +'_'+ str(get_signature())
        if not os.path.exists(file_path):
            os.makedirs(file_path)
            if not os.path.exists(file_path+'/result'):
                os.makedirs(file_path+'/result')
        code_filename = code_F.filename.split('.')[0]
        file_dir = os.path.join(os.getcwd(), file_path)
        code_file_path = os.path.join(file_dir, code_F.filename)
        code_F.save(code_file_path)
        model_file_path = os.path.join(file_dir, model_F.filename)
        model_F.save(model_file_path)
        seed_file_path = os.path.join(file_dir, seed_F.filename)
        seed_F.save(seed_file_path)
        seed_filename = seed_F.filename.split('.')[0]
        f = zipfile.ZipFile(seed_file_path,'r') # 压缩文件位置
        for file in f.namelist():
            f.extract(file,file_path)               # 解压位置
        f.close()
        p1 = Process(target=createModule, args=(shape,file_path,code_filename,load_module_function_name,file_path+'/'+seed_filename,neuron_select_strategy,threshold,neuron_to_cover_num,file_path+'/result',iteration_times,ID,q_list[ID],layer_name))
        p1.start()
        # p1.join()

        return "success"  # need to modify the html file name

    else:
        return "error"  # need to modify the html file name


@app.route('/request', methods=['GET'])
def get_message():
    get_data = request.args.to_dict()
    ID = get_data.get("ID")
    if q_list[ID].qsize()>0:
        message = q_list[ID].get()
        print('request',q_list[ID].qsize(),message)
        return message
    else:
        return "No data"


if __name__ == '__main__':
    app.run()
