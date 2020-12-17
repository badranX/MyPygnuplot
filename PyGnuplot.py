'''
By Ben Schneider

Simple python wrapper for Gnuplot
Thanks to steview2000 for suggesting to separate processes,
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
flag_reset_append = True

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

def write_arraylike_to_file(data, filename=default_append_filename, transpose=True, mode='w'):
    file = open(os.path.join(default_path, filename), mode)

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

def reset_append(arange=None, rate=None ):
    global flag_reset_append
    flag_reset_append = True


def a(*args, reset=False, filename=default_append_filename, transpose=True):
    global flag_reset_append
    names = ''
    if flag_reset_append or reset:
        append= False
        flag_reset_append=False
    else:
        append= True

    for i, data in enumerate(args):
        pyenv_filename = os.path.join(default_path, filename)
        if type(data) is np.ndarray:
            #TODO handle open exceptios in all files
            if append:
                file = open(pyenv_filename, mode='a')
            else:
                file = open(pyenv_filename, mode='w')

            if transpose:
                np.savetxt(file, data.T)
            else:
                np.savetxt(file, data)
        else:
            write_arraylike_to_file(data,filename, mode= 'a' if append else 'w')
        names = names + filename + ' '
        if i!=0:
            filename = filename[:i//10+1] + str(i)[:i]
        else:
            filename = filename + '1'
    return names



def s(*args, filename=default_filename, transpose=True):
    '''
    saves numbers arrays and text into filename (default = '.dat)
    (assumes equal sizes and 2D data sets)
    >>> s(data, filename='.dat')  # overwrites/creates .dat
    '''
    names = ''
    for i, data in enumerate(args):
        pyenv_filename = os.path.join(default_path, filename)
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
        names = names + filename + ' '
        if i!=0:
            filename = filename[:i//10+1] + str(i)[:i]
        else:
            filename = filename + '1'
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


fl = _FigureList()
