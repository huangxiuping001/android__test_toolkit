# coding:utf-8
import multiprocessing
from multiprocessing import Process, Queue
import os
from re import sub
import subprocess,shlex
import time
from datetime import datetime
import chardet
import random
import threading
import time

#第一次使用需要在cmd中使用如下指令安装chardet库包，防止出现乱码问题：
#pip install chardet
#此处输入你要执行的monkey和adb命令，当前仅分析了logcat log，没分析monkey log，有需要可以立即做，by ding，20220128
#运行后的log和结果均在和py文件同一目录下
monkey_order='adb shell monkey  --throttle 200 --ignore-crashes --ignore-timeouts --ignore-security-exceptions --ignore-native-crashes  --monitor-native-crashes -v -v -v  1000000'
logcat_order='adb logcat'
monkey_log_address=''#为空时则在py文件同目录内生成该log文件
logcat_address=''
DEVICESNAME='emulator-55567'
Time_num=48    #运行多少次monkey，单位是1cell_time
CELLTIME=3600   # 单个时间长度，单位秒

#逐行读取log文件中文件字段，识别anr和crash字段，返回一个dict
def monkey_log_analysis(monkey_log_address):
    result_dict = dict()
    anr_str = '/data/anr/anr'  # 这个还需要改
    crash_str = 'CRASH:'
    exception_str = 'FATAL EXCEPTION:'

    with open(monkey_log_address, 'r+', encoding='utf-8') as f:
        while True:
            e = f.readline()
            if e == '':
                break
            if anr_str in e:
                if anr_str in result_dict:
                    result_dict[anr_str].append(e)
                else:
                    result_dict[anr_str] = [e]

            if crash_str in e:
                if crash_str in result_dict:
                    result_dict[crash_str].append(e)
                else:
                    result_dict[crash_str] = [e]

            if exception_str in e:
                if exception_str in result_dict:
                    result_dict[exception_str].append(e)
                else:
                    result_dict[exception_str] = [e]

    return (result_dict)
    
#解决从adb获取的out流中可能有utf-8，gbk，windows-1252等各种其奇怪的编码格式导致的程序停止运行
def unicode_change(value):
    adchar=chardet.detect(value)
    
    if adchar['encoding']=='utf-8' or adchar['encoding']=='ascii':
        code='utf-8'
    elif adchar['encoding']=='Windows-1252':
        code='Windows-1252'
    else:
        code='gbk'
    
    try:
        value=value.decode(code)#解码生成unicode编码
    except UnicodeDecodeError as e:
        print('value:')
        print(value)
        print('code:')
        print(code)
        print('adchar:')
        print(adchar)
    
    return value


# monkey运行子进程，运行完成后给logcat通知已结束测试
def monkey_write_task(q,timestamp_str,monkey_order,singe_device_name):

    monkey_log_address=os.path.join(os.getcwd(),timestamp_str+'_monkey_log.txt')
    print('monkey-start')

    result=os.system(monkey_order+' > "'+monkey_log_address+'"')
    if checked_monkey_on(singe_device_name):
        print("monkey测试进行中")
    else:
        print("monkey启动失败")

    #result= subprocess.Popen(monkey_order+' > "'+monkey_log_address+'"',shell=True,stdout=subprocess.PIPE)

    #result.wait()
        
    print('monkey-end')
    q.put(True)



# logcat子进程，收到monkey结束信号后也停止logcat记录
def logcat_read_task(q,timestamp_str,logcat_order,monkey_order):

    #order=logcat_order#'adb logcat'
    logcat_log_address=os.path.join(os.getcwd(),timestamp_str+'_logcat_log.txt')
    #print("log路径"+logcat_log_address)
    print('logcat-start')
    result= subprocess.Popen(logcat_order,shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    with open(logcat_log_address, "a", encoding="utf-8") as f:
        while True:  # 将内容持续输出
            line=result.stdout.readline()#.decode("")#result.stdout.readline().decode("gbk").strip()
            #print(chardet.detect(line))
            line=unicode_change(line)
            now_time_str=datetime.strftime(datetime.now(),'%H:%M:%S ')
            f.write(str(now_time_str)+'&&'+str(line))
            if not q.empty():
                print('monkey tell logcat monkey process has finished.')
                break
        #print('logcat-running---')
            
    print('logcat-end')   

    print('logcat-log-analysis-start')
    analysis_result=monkey_log_analysis(logcat_log_address)
    result_file=timestamp_str+'_result_'
    if len(analysis_result)==0:
        result_file+='Pass.txt'
        result_file=os.path.join(os.getcwd(),result_file)
        with open(result_file,'a+', encoding="utf-8") as n:
            n.write('Run order: '+monkey_order+'\n')
    else:
        result_file+='Fail.txt'
        result_file=os.path.join(os.getcwd(),result_file)
        with open(result_file,'a+', encoding="utf-8") as r:
            r.write('\n'+'Run order: '+monkey_order+'\n\n')
            for e in analysis_result:
                r.write(str(e)+' count '+str(len(analysis_result[e]))+' : \n')
                for a in analysis_result[e]:
                    r.write('    '+a+'\n')
    print('logcat-log-analysis-end')     

def result_display():
    pass

    print("-------------monkey test end-----------------")

#获取当前已连接可用的终端信息
def devices_info2():
    d_info=subprocess.Popen('adb devices',shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.readlines()
    if len(d_info)==1:
        return False
    for e in d_info[1:]:
        #print(type(e))
        if 'device' in str(e):
            s=str(e).split(r'\t')[0][2:]
            print('tested_device: '+s)
            return True
    #print('no device')
    return False

#检查是否有正常可用
def check_info(d_name):
    check_j = True
    if devices_info(d_name) == False:
        check_j = False

    return check_j
def devices_info(d_name):
    d_info_pro=subprocess.Popen('adb devices',shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d_info=d_info_pro.stdout.readlines()
    #time.sleep(2)
    #os.system("taskkill /t /f /pid %s" % d_info_pro.pid)

    if len(d_info)==1:
        return False
    list_device=[]
    for e in d_info[1:]:
        #print(type(e))
        if 'device' in str(e):
            s=str(e).split(r'\t')[0][2:]
            list_device.append(s)

def add_seed(monkey_order):
    order_list=monkey_order.split()
    end_list=order_list[2:]
    #print(order_list)
    s_id=-1
    monkey_id=0
    result_list=order_list[:2]
    n=random.sample(range(200,10000),1)[0]#获得指定范围内的一个随机数

    for i in range(len(end_list)):
        sss=end_list[i]
        if sss.lower()=='-s':
            s_id=i+1
            continue
        
        if sss.lower()=='monkey':
            monkey_id=i
            continue
    if s_id==-1:
        result_list=result_list+end_list[:monkey_id+1]+['-s',str(n)]+end_list[monkey_id+1:]
        res_str=' '.join(result_list)
        #print(res_str)
        return res_str
    else:
        end_list[s_id]=str(n)
        result_list=result_list+end_list
        res_str=' '.join(result_list)
        #print(res_str)
        return res_str

def get_cmd_pid(id):
    d_info_pro=subprocess.Popen('tasklist ',shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d_info=d_info_pro.stdout.readlines()
    j=False
    for d in d_info[3:]:
        d_list=[]
        d_list=str(d).split()
        #print(d_list)
        if str(id) == d_list[1] :
            j=True
    return(j)

def task_kill_pid(id):
    #os.system("taskkill /t /f /pid %s" % id)
    ddd=subprocess.Popen("taskkill /t /f /pid %s" % id,shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.readlines()
    #print('ddd:')
    #print(ddd)


def checked_kill_pid(id):
    while True:
        if get_cmd_pid(id):
            task_kill_pid(id)
            time.sleep(2)
        else:
            break

def checked_kill_monkey(singe_device_name):
    while True:
        list=[]
        list=get_monkey_pid(singe_device_name)
        if len(list)==0:
            break
        else:
            kill_monkey(singe_device_name)
            time.sleep(2)

def checked_monkey_on(singe_device_name):
    for i in range(3):
      if(get_monkey_pid(singe_device_name)):
          return True
      else:
          print("monkey进程启动失败，重新启动monkey")
          os.system(monkey_order + ' > "' + monkey_log_address + '"')
          time.sleep(10)





def get_monkey_pid(singe_device_name):
    adb_ps_order = "adb shell ps "
    adb_ps_order = add_devices_seriel(adb_ps_order, singe_device_name)

    adb_ps_pro = subprocess.Popen(adb_ps_order, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    adb_ps = adb_ps_pro.stdout.readlines()
    time.sleep(2)
    # os.system("taskkill /t /f /pid %s" % adb_ps_pro.pid)
    ps_id = ''
    ps_monkey_list = []
    for e in adb_ps:
        if 'com.android.commands.monkey' in str(e):
            ps_monkey_list.append(str(e).split()[1])
    return (ps_monkey_list)


def kill_monkey(singe_device_name):
    # print(adb_ps_order)

    adb_kill_order = 'adb shell kill '
    adb_kill_order = add_devices_seriel(adb_kill_order, singe_device_name)
    print(adb_kill_order)

    ps_monkey_list = []
    ps_monkey_list = get_monkey_pid(singe_device_name)

    # os.system("taskkill /t /f /pid %s" % adb_ps.pid)
    time.sleep(2)
    print('ps_monkey:')
    print(ps_monkey_list)

    if len(ps_monkey_list) != 0:
        for e in ps_monkey_list:
            ps_kill_result_pro = subprocess.Popen(adb_kill_order + e, shell=True, stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE)
            ps_kill_result = ps_kill_result_pro.stdout.readlines()
            time.sleep(2)
            # os.system("taskkill /t /f /pid %s" % ps_kill_result_pro.pid)
            print(adb_kill_order + e)
            time.sleep(2)

    return 0

def add_devices_seriel(s,singe_device_name):

    s_list=s.split()
    if s_list[1]!='-s':
        return s.replace('adb ','adb -s '+singe_device_name+' ')
    else:
        s_list[2]=singe_device_name
        return ' '.join(s_list)

def write_monkey_time(monkey_log_address,e):
    with open(monkey_log_address, "a+", encoding="utf-8") as f:
        now = datetime.now()
        timestamp_str=datetime.strftime(now,'%Y%m%d_%H-%M-%S_')
        f.write('\n'+timestamp_str+'-------------------------------------\n')
        f.write('--------------'+e+'------------\n')

#测试主进程，启动monkey和logcat的运行子进程
def run_monkey_logcat(monkey_order,logcat_order,singe_device_name,timestamp_str):
    print("---father process start---")
    q = Queue()     # 父进程创建 Queue，并传递给子进程
    logcat_process = Process(target=logcat_read_task, args=(q,timestamp_str, logcat_order, monkey_order))
    monkey_process = Process(target=monkey_write_task, args=(q,timestamp_str, monkey_order,singe_device_name))
    monkey_process.start()
    logcat_process.start()
    time.sleep(CELLTIME)
    monkey_process.terminate()
    checked_kill_monkey(singe_device_name)
    print('monkey-end')
    q.put(True)
    print("---wait child process to end ---")
    #monkey_process.join()
    logcat_process.join()
    print("---father process end---")

def get_single_devices_name():
    d_info_pro=subprocess.Popen('adb devices',shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d_info=d_info_pro.stdout.readlines()
    #time.sleep(2)
    #os.system("taskkill /t /f /pid %s" % d_info_pro.pid)

    list_device=[]
    for e in d_info[1:]:
        #print(type(e))
        if 'device' in str(e):
            s=str(e).split(r'\t')[0][2:]
            list_device.append(s)
    if len(list_device)==1:
        return list_device[0]
    else:
        return('000')

if __name__ == '__main__':
    multiprocessing.freeze_support()
    if check_info(DEVICESNAME):
        singe_device_name = get_single_devices_name()
        if singe_device_name == '000':
            singe_device_name = DEVICESNAME
        monkey_order=add_seed(monkey_order)
        print('monkey_order: '+monkey_order)
        print('logcat_order: '+logcat_order)
        r=input('decide to run monkey ?y/n ')#测试运行开启前信息引导
        if r.lower()=='y':
            for i in range(Time_num):
                now = datetime.now()
                timestamp_str = datetime.strftime(now, '%Y%m%d_%H-%M-%S_')
                os.system("adb shell logcat -c")
                print("==========================这是第"+str(i+1)+"次运行=============================================")
                run_monkey_logcat(monkey_order,logcat_order,singe_device_name,timestamp_str)
        else:
            print('stoped')
    else:
        print('no device')
    print("######monket test run success#########")
   # sss=input('tap to end.')

    

