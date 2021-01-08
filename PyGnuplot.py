'''
By Ben Schneider

Simple python wrapper for Gnuplot Thanks to steview2000 for suggesting to separate processes,
    jrbrearley for help with debugging in python 3.4+

Example:
    import PyGnuplot as gp
    import numpy as np
    X = np.arange(10)
    Y = np.sin(X/(2*np.pi))
    Z = Y**2.0
    gp.s([X,Y,Z])  # saves data into tmp.dat
    gp.c('plot "tmp.dat" u 1:2 w lp)  # send 'plot instructions to gnuplot'
    gp.c('replot "tmp.dat" u 1:3' w lp)
    gp.p('myfigure.ps')  # creates postscript file

'''

#TODO raise error when TYPE is not matched either striing or Array
#TODO previous one provide an integer and a strange error is showed 

import numpy as np
import re
from subprocess import Popen as _Popen, PIPE as _PIPE
import sys
import os
import time
import inspect

isPytorch = False
try:
    import torch
except:
    isPytorch = False
else:
    isPytorch = True


isNotebook = False
try:
    from IPython.display import Image, display
except:
    isNotebook = False
else:
    isNotebook = True

default_term = 'x11'  # change this if you use a different terminal
default_filename = 'data'  # change this if you use a different terminal
default_append_file = 'append'  # change this if you use a different terminal
default_append_filename = '.append' # change this if you use a different terminal
default_folder_name = '.gnuplot'
default_path = os.getcwd()
flag_reset_append = False

class _FigureList(object):
    def __init__(self):
        global default_path
        try:
            if not os.path.exists(default_folder_name):
                os.makedirs(default_folder_name)
        except OSError as e:
            print("Couldn't create a hidden .gnuplot folder, so generated files (.dat, .append...) will be created in the current director. See error:\n" + str(e))
            default_path = os.getcwd()
        else:
            default_path = os.path.join(os.getcwd(), default_folder_name)
        try:
            proc = _Popen(['gnuplot', '-p'], shell=False, stdin=_PIPE, cwd=default_path, universal_newlines=True)  # persitant -p
            self.instance = {0 : [proc, default_term]}  # {figure number : [process, terminal type]}
        except Exception as e:
            print("Couldn't run gnuplot, probably not installed. you wont be able to use the c(.) method: \n" + str(e))
        self.n = 0  # currently selected Figure

        # Format:
        # instance[self.n][0] = process
        # instance[self.n][1] = terminal


def figure(number=None, args = '-p'):
    '''Make Gnuplot plot in a new Window or update a defined one figure(num=None, term='x11'):
    >>> figure(2)  # would create or update figure 2
    >>> figure()  # simply creates a new figure
    returns the new figure number
    '''
    if not isinstance(number, int):  # create new figure if no number was given
        number = max(fl.instance) + 1

    if number not in fl.instance:  # number is new
        proc = _Popen(['gnuplot', args], shell=False, stdin=_PIPE, universal_newlines=True)
        fl.instance[number] = [proc, default_term]

    fl.n = number
    c('set term ' + str(fl.instance[fl.n][1]) + ' ' + str(fl.n))
    return number


def c(command):
    '''
    Send command to gnuplot
    >>> c('plot sin(x)')
    >>> c('plot ".dat" u 1:2 w lp)
    '''
    proc = fl.instance[fl.n][0]  # this is where the process is
    proc.stdin.write(command + '\n')  # \n 'send return in python 2.7'
    proc.stdin.flush()  # send the command in python 3.4+


def in_notebook():
    global isNotebook, default_term
    if isNotebook:
        default_term = 'png'
        c('set term png')
        c('set output ".img.dat.png"')
    return isNotebook

#TODO notebook only
def show():
    if isNotebook:
        display(Image(filename='.img.dat.png'))

def sv(data):
    tmp = """$dat << EOD\n"""

    if type(data) is np.ndarray:
        arr_str = np.array2string(data)
        arr_str= re.sub('[\[\]]','',arr_str)
        tmp +=arr_str + "\nEOD"
    else:        
        columns = len(data)
        rows = len(data[0])
        for j in range(rows):
            for i in range(columns):
                tmp += (str(data[i][j])) + ' '
            tmp+='\n'
        tmp += "EOD"
    c(tmp)

def write_arraylike_to_file( file, data, transpose):

    columns = len(data)
    rows = len(data[0])

    if transpose: 
        for j in range(rows):
            for i in range(columns):
                file.write(str(data[i][j]))
                file.write(' ')
            file.write('\n')
            if j % 1000 == 0 :
                file.flush()  # write once after every 1000 entries
    else:
        for i in range(columns):
            for j in range(rows):
                file.write(str(data[i][j]))
                file.write(' ')
            file.write('\n')
            if j % 1000 == 0 :
                file.flush()  # write once after every 1000 entries
    file.close()  # write the rest



a_counters = {}#counter=0 means empty file
a_names = {}#counter=0 means empty file
a_files = {}

def remove_files():
    #copy/paste from SO
    for f in os.listdir(default_folder_name):
        os.remove(os.path.join(default_folder_name, f)) 


def free_a(rm=False):
    global a_files, a_counters
    for files in a_files:
        for f in files:
            try:
                f.close()
            except Exception as e:
                #TODO bug: str object has no attribute close
                #print('TODO: couldnt close file, theres a bug. A file is a str sometimes, maybe python bug')
                #print(e)
                pass

            if rm:
                try:
                    os.remove(f.name)
                except:
                    try:
                        open(f.name,'w').close()
                    except:
                        pass
    a_counters.clear()
    a_files.clear()

def free(rm=False):
    free_a(rm)


def get_var_name(var, default=None):

    frame = inspect.currentframe().f_back.f_back.f_back #we called from write_general->s(.) or a( .) -> user
    caller_local_vars = frame.f_locals.items()
    possible_names= [get_var_name for get_var_name, var_val in caller_local_vars if var_val is var]
    return default if len(possible_names)==0 else possible_names[0]

def getID():
    frame = inspect.currentframe().f_back.f_back
    info = inspect.getframeinfor(frame)
    return info.filename + '_' + info.lineno + '_' + info.lineno

def get_names(args, ID, same, counter):
    #get filenames
    if ID in a_names and counter !=0: #if counter=0 need to reset
        return a_names[ID]

    #get file names
    filenames=[ID]
    for i,  _ in enumerate(args):
        if i !=0:
            filenames.append(ID + str(i))

    varnames=[]
    for i,  arg in enumerate(args):
        sub_varnames = []
        if type(arg) is dict:
            sub_varnames = list(arg.keys())
        elif same:
            if type(arg) is tuple:
                assert(len(arg)!=0)
                for j in range(len(arg)):
                    var_name =  get_var_name(arg[j], ID  + '-' + str(j))
                    sub_varnames.append(var_name)
            else:
                var_name =  get_var_name(arg, ID)
                sub_varnames.append(var_name)#bcz it returns a list of lists at the end
        else:
            sub_varnames = []
            if type(args[i]) is tuple:
                sub_varnames += [ID + '-' + str(index) for index, _ in enumerate(args[i])]
            else:
                sub_varnames.append(ID + '-' + str(0))
            varnames.append(sub_varnames)
        varnames.append(sub_varnames)

    a_names[ID] = filenames, varnames
    return filenames, varnames


def _free_a(ID, filenames):
    global a_files
    if ID in a_files:
        for f in a_files[ID]:
            f.close()
        a_files.pop(ID, None)
    if ID in a_counters:
        a_counters[ID] = 0

def _init_files_a(ID, filenames):
    '''empty files and initialize a_files'''
    '''save a_files[ID] list of files descriptors in the same order as filenames'''
    files = []
    global a_files
        #remove files in descriptors
    if ID in a_files:
        for f in a_files[ID]:
            f.close()
            try:#TODO recheck emptying file
                os.remove(f.name)#TODO maybe open(path,'w').close()
            except:
                open(f.name, 'w').close()
                pass
        a_files.pop(ID, None)

    #init file list in order of filenames, and delete files if found or empty them files=[]
    for fname in filenames:
        path = os.path.join(default_folder_name,fname)
        try:#TODO refactor
            os.remove(path)#TODO maybe open(path,'w').close()
        except OSError as e:#TODO NotEmplementedException
            open(path, 'w').close()
            pass
        file = open(path, 'a')
        files.append(file)
    a_files[ID] = files
    return files




def a(*args, **kwargs):#arange, final_count period, sequence, append=False, ID=default_append_filename, persist_file=True transpose=True):
    '''kwargs is either arange period sequence otherwise throw error'''
    '''counter increases only when it writes'''
    global  a_counters, a_files
    comment= kwargs.get('comment', True)
    same= kwargs.get('same', False)

    ID = str(kwargs.get('ID', default_append_file))

    #init counter
    if 'counter' in kwargs:
        counter = kwargs['counter']
        a_counters[ID]= counter 
    elif ID not in a_counters:
        a_counters[ID] = 0
    counter = a_counters[ID]

    #init files filenames, 
    filenames, varnames= get_names(args,ID= ID,same= same, counter= counter)
    if counter == 0:#if 0 then init files
        _init_files_a(ID, filenames)#save file descriptors


    if 'final_count' in kwargs:
        final_count = kwargs['final_count']
        if counter >= final_count:
            _free_a(ID, filenames)
            return ' '.join(filenames)

    #check sequence and period
    if 'sequence' in kwargs:
        if counter not in kwargs['sequence']:
            _free_a(ID, filenames)
            return ' '.join(filenames)
    elif 'period' in kwargs:
        if (counter + 1) % kwargs['rate'] == 0:
            _free_a(ID, filenames)
            return ' '.join(filenames)
    
    files = a_files[ID]
    for i, data in enumerate(args):
        write_general(files[i], data, counter, comment, varnames[i])
    a_counters[ID] += 1
    return ' '.join(filenames)


#TODO alter file as a variable name
def write_general(file, data, counter, comment, variable_names):
    #i is data index in parameters/args
    if type(data) is str:
        if comment:
            file.write('#' + str(counter) + '\n')
        file.write(data)
        if comment and data[-1] != '\n':
            file.write('\n')
        file.flush()
        return
    else:
        out, lengths= make_one_numpy_arr(data, variable_names)
        if counter == 0:
            column_names = []
            for index, l in enumerate(lengths):
                for c in range(l):
                    column_names.append(variable_names[index] + '[' + str(c) + ']')
            file.write('# ' + ' '.join(column_names) + '\n')
        if comment:
            file.write('#' + str(counter) + '\n')
        np.savetxt(file, out)
        file.flush()


def make_one_numpy_arr(data, variable_names):
    #variable_names for log attempt
    if type(data) is dict:
        data = list(data.values())
    elif type(data) is tuple:
        data = list(data)
    else:
        data = [data]
    indices = []
    #make sure everything is numpy of 2 dimensions
    for i, arr in enumerate(data):
        if type(arr) is list:
            data[i]= arr = np.array(arr)
        elif isPytorch and torch.is_tensor(arr):
            data[i] = arr = arr.detach().numpy()

        if len(arr.shape)==0:
            data[i] = arr = arr[..., None, None]
        elif len(arr.shape)==1:
            data[i] = arr = arr[..., None]
        elif len(arr.shape)>2:
            raise ValueError( str(variable_names[i]) + ' has ' + str(len(arr.shape)) + ' dimensions ::' +  ' one or two dimensions needed')
        elif len(arr.shape)==0:
            raise ValueError( str(variable_names[i]) + ' has ' + str(len(arr.shape)) + ' dimensions ::' + ' one or two dimensions needed')
    return np.hstack(tuple(data)), list(map(lambda x: len(x[0]), data)) #one_numpy_arr, list of row lengths




def s(*args, ID=default_filename, comment=False, same=False):
    '''
    saves numbers arrays and text into ID (default = '.dat)
    (assumes equal sizes and 2D data sets)
    >>> s(data, ID='.dat')  # overwrites/creates .dat
    '''
    counter =0 #reusing append helper functions
    #varnames is a list of lists
    filenames, varnames = get_names(args, ID= ID,same= same, counter =counter)
    files = _init_files_a(ID, filenames)
    for i, data in enumerate(args):
        write_general(files[i], data, counter, comment, varnames[i])
    for f in files:
        f.close()  # write the rest
    a_files.pop(ID, None)#saved by _init_files_a
    return ' '.join(filenames)

def plot(data, filename='tmp.dat'):
    ''' Save data into filename (default = 'tmp.dat') and send plot instructions to Gnuplot'''
    s(data, filename)
    c('plot "' + filename + '" w lp')


def p(filename='tmp.ps', width=14, height=9, fontsize=12, term=default_term):
    '''Script to make gnuplot print into a postscript file
    >>> p(filename='myfigure.ps')  # overwrites/creates myfigure.ps
    '''
    c('set term postscript size ' + str(width) + 'cm, ' + str(height) + 'cm color solid ' +
      str(fontsize) + " font 'Calibri';")
    c('set out "' + filename + '";')
    c('replot;')
    c('set term ' + str(term) + '; replot')


def pdf(filename='tmp.pdf', width=14, height=9, fontsize=12, term=default_term):
    '''Script to make gnuplot print into a pdf file
    >>> pdf(filename='myfigure.pdf')  # overwrites/creates myfigure.pdf
    '''
    c('set term pdf enhanced size ' + str(width) + 'cm, ' + str(height) + 'cm color solid fsize ' +
      str(fontsize) + " fname 'Helvetica';")
    c('set out "' + filename + '";')
    c('replot;')
    c('set term ' + str(term) + '; replot')



#prevent ipython from maintaining the values
a_counters.clear()
a_files.clear()
fl = _FigureList()
