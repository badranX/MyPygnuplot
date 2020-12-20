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


try:
    from IPython.display import Image, display
except:
    pass
default_term = 'x11'  # change this if you use a different terminal
default_filename = '.dat'  # change this if you use a different terminal
default_append_filename = '.append' # change this if you use a different terminal
default_folder_name = '.gnuplot'
default_path = os.getcwd()
is_in_notebook = False
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

        proc = _Popen(['gnuplot', '-p'], shell=False, stdin=_PIPE, cwd=default_path, universal_newlines=True)  # persitant -p
        self.instance = {0 : [proc, default_term]}  # {figure number : [process, terminal type]}
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



def in_notebook(isNotebook=True):
    global is_in_notebook
    if not isNotebook:
        c("set term " +  default_term)
        is_in_notebook= False
    else:
        c('set term png')
        c('set output ".img.dat.png"')
        is_in_notebook= True

    #TODO notebook only
    def show():
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
def free_a(rm=True):
    global a_files, a_counters
    if rm:
        for f in a_files:
            file = a_files[f]
            #os.remove(file.ID)
            file.close()
    a_counters.clear()
    a_files.clear()

def get_var_name(var, default=None):

    frame = inspect.currentframe().f_back.f_back
    caller_local_vars = frame.f_locals.items()
    possible_names= [get_var_name for get_var_name, var_val in caller_local_vars if var_val is var]
    return default if len(possible_names)==0 else possible_names[0]

def getID():
    frame = inspect.currentframe().f_back.f_back
    info = inspect.getframeinfor(frame)
    return info.filename + '_' + info.lineno + '_' + info.lineno

def get_names(*args, ID, same):
    #get filenames
    global filenames
    if ID in a_names:
        return a_names[ID]

    filenames=[]
    varnames=[]
    if same:
        for i,  arg in enumerate(args):
            sub_varnames = []
            filename = ''
            default_filename = ID + (str(i) if i!=0 else '')
            if type(arg) is tuple:
                assert(len(arg)!=0)
                for j in range(len(arg)):
                    var_name =  get_var_name(arg[j], default_filename  + '-' + str(j))
                    filename += var_name + ('_' if j==len(arg) else '')
                    sub_varnames.append(var_name)
            else:
                filename = get_var_name(arg, default_filename + '-' + str(0))
                sub_varnames.append(filename)
            varnames.append(sub_varnames)
            filenames.append(filename)
    else:
        filenames.append(ID)
        for i,  _ in enumerate(args):
            sub_varnames = []
            if type(args[i]) is tuple:
                sub_varnames += [ID + '-' + str(index) for index, _ in enumerate(args[i])]
            else:
                sub_varnames.append(ID + '-' + str(0))
            varnames.append(sub_varnames)
            if i !=0:
                filenames.append(ID + str(i))
    a_names[ID] = filenames, varnames
    return filenames, varnames


def a(*args, **kwargs):#arange, final_count period, sequence, append=False, ID=default_append_filename, persist_file=True transpose=True):
    '''kwargs is either arange period sequence otherwise throw error'''
    '''counter increases only when it writes'''

    global  a_counters, a_files
    transpose = kwargs.get('transpose',False)
    comment= kwargs.get('comment', True)
    same= kwargs.get('same', False)

    ID = str(kwargs.get('ID', default_filename))

    #init counter
    if 'counter' in kwargs:
        counter = kwargs['counter']
        a_counters[ID]= counter 
    elif ID not in a_counters:
        a_counters[ID] = 0
    counter = a_counters[ID]


    #init files
    filenames, varnames= get_names(args,ID= ID,same= same)
    if counter == 0:#first time, so initialize
        mode = 'w'
        for fname in filenames:
            if fname in a_files:
                a_files[fname].close()
                del a_files[fname]
            path = os.path.join(default_folder_name,fname)
            try:
                os.remove(path)
            except OSError as e:#TODO NotEmplementedException
                pass

            #pyenv_filename = os.path.join(default_path, fname)
            #open(pyenv_filename, mode=mode).close()

    if 'final_count' in kwargs:
        final_count = kwargs['final_count']
        if counter >= final_count:
            return None
    mode = 'a'
    files = []
    tmp =[]
    for fname in filenames:
        pyenv_filename = os.path.join(default_path, fname)
        file = open(pyenv_filename, mode=mode)
        file.write('')
        file.flush()
        tmp.append(file)
        a_files[fname] = file
    if len(tmp)==0:
        #no arrays were provided
        print('no arrays were provided')
        return None
    files = tmp


    #check sequence and period
    if 'sequence' in kwargs:
        if counter not in kwargs['sequence']:
            return ' '.join(filenames)
    elif 'period' in kwargs:
        if (counter + 1) % kwargs['rate'] == 0:
            return ' '.join(filenames)
    
    print(len(args))
    print(len(filenames))
    for i, data in enumerate(args):
        if counter == 0:
            files[i].write('# ' + ' '.join(varnames[i]) + '\n')
        data = if_numpylike_make_one_numpy_arr(data)
        if(comment):
            files[i].write('#' + str(counter) + '\n')
        if type(data) is str:
            files[i].write(data)
            if comment and data[-1] != '\n':
                files[i].write('\n')
        if type(data) is np.ndarray:
            if transpose:
                np.savetxt(files[i], data.T)
            else:
                np.savetxt(files[i], data)
            files[i].flush()
        elif type(data) == str:
            files[i].write(data)
            if comment and data[-1] != '\n':
                files[i].write('\n')
            files[i].flush()
        else:
            write_arraylike_to_file(files[i], data, transpose)
    a_counters[ID] += 1
    return ' '.join(filenames)


#TODO alter file as a variable name
def write_general(file, data):
    row=0
    while True:
        row_str = ''
        column=0
        for arr in data:
            try:
                arr[row]
            except IndexError:
                return
            try:
                arr[0][0]
            except TypeError:
                arr = np.array(arr)
                arr = arr[..., None]
            column= 0
            for j in range(len(arr[row])):
                row_str += str(arr[row][column]) + ' ' 
                column += 1
        file.write(row_str[:-1] + '\n')
        file.flush()#TODO make it less often
        row += 1



        
            


        


def if_numpylike_make_one_numpy_arr(data):
    '''it converst data into a list'''#TODO
    #If numpy like will transfer everything into one array, otherwise a tuple or a list will be enumerable for normal writing to file, so Im converting data to list
    if type(data) is tuple:
        data = list(data) ####
        isNumpyLike = len(data) > 0
        for i, x in enumerate(data):
            isNumpyLike = isNumpyLike and (isPytorch and \
                                torch.is_tensor(x) or \
                                type(x) is np.ndarray)
            if isPytorch and torch.is_tensor(x):
                x = x.detach().numpy() #TODO do we need this?
                data[i]=x
            if isNumpyLike and len(x.shape)==1: #both numpy and torch implement len(.)
                x= x[..., None]
                data[i]=x

        if isNumpyLike:
            data = np.concatenate(tuple(data),axis=1)#TODO what about 1D array!!
    elif isPytorch and torch.is_tensor(data):
        data = data.detach().numpy()
    return data

def s(*args, ID=default_filename, transpose=False):
    '''
    saves numbers arrays and text into ID (default = '.dat)
    (assumes equal sizes and 2D data sets)
    >>> s(data, ID='.dat')  # overwrites/creates .dat
    '''
    names = ''
    for i, data in enumerate(args):
        data = if_numpylike_make_one_numpy_arr(data)
        pyenv_filename = os.path.join(default_path, ID)
        if type(data) is np.ndarray:
            if transpose:
                np.savetxt(pyenv_filename, data.T)
            else:
                np.savetxt(pyenv_filename, data)
        else:
            file = open(pyenv_filename, 'w')

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
        names = names + ID + ' '
        if i!=0:
            ID = ID[:i//10+1] + str(i)[:i]
        else:
            ID = ID + '1'
    return names

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
