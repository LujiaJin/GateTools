#!/usr/bin/env python

import os
import tempfile
import shutil
import click
import socket
from distutils.spawn import find_executable
import colorama



def get_dns_domain():
    return socket.getfqdn().split('.', 1)[1]

class ParserMacro:
    def __init__(self):
        self.parserAllFiles = {}
        self.aliasToGate = {}
        self.aliasNumber = 0

    def parseMacFiles(self, fullMacroDir, mainMacroFile):
        macFiles = [mainMacroFile]
        while len(macFiles) != 0:
            self.parserAllFiles[macFiles[0]] = []
            with open(os.path.join(fullMacroDir, macFiles[0])) as f:  # open file
                for line in f:
                    self.parserAllFiles[macFiles[0]] += [line]
                    if not line.startswith('#') and not line == '\n':
                        line = line.strip() #Remove trailing whitespace
                        if line.startswith('/control/execute'):
                            splitLine = line.split(" ")
                            splitLine = [x for x in splitLine if x]
                            macFiles.append(splitLine[1])
            macFiles = macFiles[1:]

    def parseAttributes(self):
        self.parserAttributes = {}
        self.parserAlias = {}
        for file in self.parserAllFiles:
            for index, line in enumerate(self.parserAllFiles[file]):
                if not line.startswith('#') and not line == '\n':
                    line = line.strip() #Remove trailing whitespace
                    if line.startswith('/gate/application/setTimeStart'):
                        self.parserAttributes["setTimeStart"] = [file, index]
                    elif line.startswith('/gate/application/setTimeSlice'):
                        self.parserAttributes["setTimeSlice"] = [file, index]
                    elif line.startswith('/gate/application/setTimeStop'):
                        self.parserAttributes["setTimeStop"] = [file, index]
                    elif line.startswith('/gate/application/setTotalNumberOfPrimaries'):
                        self.parserAttributes["setTotalNumberOfPrimaries"] = [file, index]

                    #Parse alias
                    splitLine = line.split(" ")
                    splitLine = [x for x in splitLine if x]
                    if splitLine[0] == '/control/alias':
                        self.parserAlias[splitLine[1]] = [file, index]


    def setAttributes(self, attribute, valuesForAllJobs):
        line = self.parserAllFiles[self.parserAttributes[attribute][0]][self.parserAttributes[attribute][1]]
        line = line.strip() #Remove trailing whitespace
        splitLine = line.split(" ")
        splitLine = [x for x in splitLine if x]
        if not isinstance(valuesForAllJobs[0], list):
            splitLine[1] = '{' + attribute + '_' + str(self.aliasNumber) + '}'
            self.aliasToGate[attribute + '_' + str(self.aliasNumber)] = valuesForAllJobs
            self.aliasNumber += 1
        else:
            for index, value in enumerate(valuesForAllJobs[0]):
                splitLine[index + 1] = '{' + attribute + '_' + str(self.aliasNumber) + '}'
                self.aliasToGate[attribute + '_' + str(self.aliasNumber)] = valuesForAllJobs[:][index]
                self.aliasNumber += 1
        self.parserAllFiles[self.parserAttributes[attribute][0]][self.parserAttributes[attribute][1]] = " ".join(splitLine) + '\n'

    # Return the value of the attribute, not the command
    # Check if containing alias, in such a case, replace it by the alias value if it exist, else raise an error
    def getAttributes(self, attribute):
        line = self.parserAllFiles[self.parserAttributes[attribute][0]][self.parserAttributes[attribute][1]]
        line = line.strip()
        line = line.split(" ")
        splitLine = []
        for x in line:
            if x.startswith('{') and x.endswith('}'):
                if x[1:-1] in self.parserAlias:
                    print(colorama.Fore.YELLOW + "WARNING: attribute \"" + attribute + "\" is an alias " + x +
                          ". Prefer a value instead of an alias" + colorama.Style.RESET_ALL)
                    splitLine += [self.getAlias(x[1:-1])]
                else:
                    print(colorama.Fore.RED + "ERROR: attribute \"" + attribute + "\" is an alias " + x + colorama.Style.RESET_ALL)
                    print(colorama.Fore.RED + "And the alias was not found in macro files" + colorama.Style.RESET_ALL)
                    exit(1)
            elif x:
                splitLine += [x]
        return splitLine[1:]


    def getAlias(self, alias):
        if not alias in self.parserAlias:
            print(colorama.Fore.RED + "ERROR: alias " + alias + " is not found in macro files" + colorama.Style.RESET_ALL)
            exit(1)
        line = self.parserAllFiles[self.parserAlias[alias][0]][self.parserAlias[alias][1]]
        line = line.strip()
        splitLine = line.split(" ")
        splitLine = [x for x in splitLine if x]
        return " ".join(splitLine[2:]) #Do not return the command and the name of the alias


    def writeMacFiles(self, outputDir):
        for file in self.parserAllFiles:
            with open(os.path.join(outputDir, file), 'w') as f:
                for element in self.parserAllFiles[file]:
                    f.write(element)


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--mac', default='mac/main.mac', help='Input mac filename')
@click.option('--j', default=10, help='Number of jobs/core')
@click.option('--numberprimaries', default=0, help='Total number of primaries for all jobs')
@click.option('--releasedir', default='', help='Gate release directory for the jobs (none means Gate in PATH)')
@click.option('--paramtogate', default='', help='Parameters for Gate')
@click.option('--timestart', default=0.0, help='Set time start for the first job')
@click.option('--timeslice', default=0.0, help='Set time duration for one job')
@click.option('--timestop', default=0.0, help='Set time stop for the last job')
@click.option('--splittime', is_flag=True, help='Divide time duration into the number of jobs')
@click.option('--output', default='', help='Output folder (default: run.XXX)')
@click.option('--copydata', is_flag=True, help='Hard copy data into run.XXX folder (default: symbolic link)')
@click.option('--dry', is_flag=True, help='If dry is set, copy all files, write the submission command lines but do not execute them')

def runJobs(mac, j, numberprimaries, releasedir, paramtogate, timestart, timeslice, timestop, splittime, output, copydata, dry):
    """
    \b
    Run Gate jobs
    """

    #Control if options are correct:
    if numberprimaries != 0:
        if timestart != 0 or timeslice != 0 or timestop != 0:
            print(colorama.Fore.RED + "ERROR: Cannot use time options (timestart, timeslice or timestop) with numberprimaries." + colorama.Style.RESET_ALL)
            exit(1)

    directoryJobFiles = os.path.dirname(os.path.abspath(__file__))
    jobFile = ""
    # Take the correct job file according to the cluster name
    if get_dns_domain() == 'in2p3.fr':
        jobFile = os.path.join(directoryJobFiles, 'gate_job_ccin2p3.job')
    else:
        jobFile = os.path.join(directoryJobFiles, 'gate_job_cluster.job')
    if not os.path.isfile(jobFile):
        print(colorama.Fore.RED + 'ERROR: The job file does not exist: ' + jobFile + colorama.Style.RESET_ALL)
        exit(1)

    # Get the release of Gate used for the simulation
    if (releasedir == ''):
        releasedir = os.path.dirname(find_executable('Gate'))
        if releasedir == '':
            print(colorama.Fore.RED + 'ERROR: No Gate found in PATH' + colorama.Style.RESET_ALL)
            exit(1)
        else:
            print('Found Gate in folder: ' + releasedir)
            releasedir = 'NONE'
    else:
        if not os.path.isdir(releasedir):
            print(colorama.Fore.RED + 'ERROR: This folder does not exist: ' + releasedir + colorama.Style.RESET_ALL)
            exit(1)
        if not os.path.isfile(os.path.join(releasedir, 'Gate')):
            print(colorama.Fore.RED + 'ERROR: There is no release of Gate in that folder: ' + releasedir + colorama.Style.RESET_ALL)
            exit(1)

    # Get macro folder and files
    fullMacroDir = os.path.join(os.getcwd(), os.path.dirname(os.path.dirname(mac)))
    relativeMacroDir = os.path.dirname(os.path.dirname(mac))
    mainMacroFile = mac[len(relativeMacroDir)+1:]
    if relativeMacroDir == '':
        relativeMacroDir = '.'
        mainMacroFile = mac
    if not os.path.isdir(os.path.join(fullMacroDir, 'mac')):
        print(colorama.Fore.RED + 'ERROR: The mac folder does not exist: ' + os.path.join(fullMacroDir, 'mac') + colorama.Style.RESET_ALL)
        exit(1)
    if not os.path.isdir(os.path.join(fullMacroDir, 'data')):
        print(colorama.Fore.RED + 'ERROR: The data folder does not exist: ' + os.path.join(fullMacroDir, 'data') + colorama.Style.RESET_ALL)
        exit(1)
    if not os.path.isfile(mac):
        print(colorama.Fore.RED + 'ERROR: The mac file does not exist: ' + mac + colorama.Style.RESET_ALL)
        exit(1)

    # Create output directory
    outputDir = output
    if outputDir == '':
        outputDir = tempfile.mkdtemp(prefix='run.', dir=fullMacroDir)
    elif not os.path.isdir(outputDir):
        os.mkdir(outputDir)
    runId = outputDir[outputDir.find('run.') + 4:]
    print('Run Id is: ' + runId)

    # Find qsub
    qsub = shutil.which('qsub')
    if qsub is None:
        print(colorama.Fore.YELLOW + 'WARNING: qsub is not found. Simply run Gate on multpile cores.' + colorama.Style.RESET_ALL)

    # Parameter files
    paramFileName = os.path.join(outputDir, 'params.txt')
    paramFile = open(paramFileName, "w")
    paramFile.write('njobs = ' + str(j))
    paramFile.write('macro = ' + mac)
    if paramtogate != '':
        paramFile.write('param = ' + paramtogate)
    paramFile.close()

    #Parse macro files and sub-Macro
    os.mkdir(os.path.join(outputDir, 'mac'))
    parserMacro = ParserMacro()
    parserMacro.parseMacFiles(fullMacroDir, mainMacroFile)
    parserMacro.parseAttributes()

    # Copy data
    if copydata:
        shutil.copytree(os.path.join(fullMacroDir, 'data'), os.path.join(outputDir, 'data'))
    else:
        os.symlink(os.path.join(fullMacroDir, 'data'), os.path.join(outputDir, 'data'))

    # Set number of Primaries
    if numberprimaries != 0:
        parserMacro.setAttributes('setTotalNumberOfPrimaries', j*[int(numberprimaries/j)])

    # Set time options
    if timestart != 0:
        parserMacro.setAttributes('setTimeStart', j*[timestart])
    if timeslice != 0:
        parserMacro.setAttributes('setTimeSlice', j*[timeslice])
    if timestop != 0:
        parserMacro.setAttributes('setTimeStop', j*[timestop])

    #Manage split time option
    #Divide the time into j range of time
    if splittime:
        startTime = float(parserMacro.getAttributes('setTimeStart')[0])
        stopTime = float(parserMacro.getAttributes('setTimeStop')[0])
        slicedTime = (stopTime - startTime)/j
        arrayStartTime = []
        arrayStopTime = []
        for i in range(0, j):
            arrayStartTime += [startTime + i*slicedTime]
            arrayStopTime += [startTime + (i+1)*slicedTime]
        parserMacro.setAttributes('setTimeStart', arrayStartTime)
        parserMacro.setAttributes('setTimeStop', arrayStopTime)

    #Write mac files into output folder
    parserMacro.writeMacFiles(outputDir)

    # Run jobs
    for i in range(0, j):
        #Set paramtogate with alias for each job
        paramtogateJob = paramtogate
        if len(parserMacro.aliasToGate) != 0:
            indexAlias = paramtogate.find('-a')
            if indexAlias != -1:
                paramtogateEnd = paramtogate[indexAlias+3:]
                paramtogateJob = paramtogate[:indexAlias+2]
                for alias in parserMacro.aliasToGate:
                    paramtogateJob += '[' + alias + ',' + str(parserMacro.aliasToGate[alias][i]) + ']'
                    paramtogateJob += paramtogateEnd
            else:
                paramtogateJob += ' -a '
                for alias in parserMacro.aliasToGate:
                    paramtogateJob += '[' + alias + ',' + str(parserMacro.aliasToGate[alias][i]) + ']'

        if qsub is None:
            command = 'PARAM=\" ' + paramtogateJob + \
                      '\" INDEX=' + str(i) + \
                      ' INDEXMAX=' + str(j) + \
                      ' OUTPUTDIR=' + outputDir + \
                      ' RELEASEDIR=' + releasedir + \
                      ' MACROFILE=' + os.path.join(outputDir, mainMacroFile) + \
                      ' MACRODIR=' + outputDir + \
                      ' PBS_JOBID=\"local_' + str(i) + \
                      '\" bash ' + jobFile
        elif get_dns_domain() == 'in2p3.fr':
            command = 'qsub -o ' + outputDir + \
                      ' -e ' + outputDir + \
                      ' -l sps=1 -N \"gate.' + runId + \
                      '\" -v \"PARAM=\"' + paramtogateJob + \
                      '\",INDEX=' + str(i) + \
                      ',INDEXMAX=' + str(j) + \
                      ',OUTPUTDIR=' + outputDir + \
                      ',RELEASEDIR=' + releasedir + \
                      ',MACROFILE=' + os.path.join(outputDir, mainMacroFile) + \
                      ',MACRODIR=' + outputDir + \
                      '\" ' + jobFile
        else:
            command = 'qsub -N \"gatejob.' + runId + \
                      ' -o ' + outputDir + \
                      ' -v \"PARAM=\"' + paramtogateJob + \
                      '\",INDEX=' + str(i) + \
                      ',INDEXMAX=' + str(j) + \
                      ',OUTPUTDIR=' + outputDir + \
                      ',RELEASEDIR=' + releasedir + \
                      ',MACROFILE=' + os.path.join(outputDir, mainMacroFile) + \
                      ',MACRODIR=' + outputDir + \
                      '\" ' + jobFile
        if dry:
            print(command)
        else:
            os.system(command)



if __name__ == "__main__":
    colorama.init()
    runJobs()