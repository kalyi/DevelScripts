#!/usr/bin/env python3
# -*- coding: utf8; -*-
#
# Copyright (C) 2016 : Kathrin Hanauer
#
# Checks whether a file contains the specified license header and,
# if negative, tries to update it.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

"""Checks and, if necessary, fixes license headers."""

import argparse

################################################################################
# adjust as needed
################################################################################
commentTokens = {
 'c'     : { 'line' : [ '//' ], 'block': [ ('/*','*/')]},
 'python': { 'line' : [ '#' ],  'block': [ ('"""','"""')]},
 'bash'  : { 'line' : [ '#' ],  'block': [ ]},
 'java'  : { 'line' : [ '//' ], 'block': [ ('/*','*/')]}
}

fileExtensions = {
 'c'     : [ ".c", ".cpp", ".h", ".hpp" ],
 'python': [ ".py" ],
 'bash'  : [ ".sh" ],
 'java'  : [ ".java" ]
}

aliases = { 'sh' : 'bash' }

licenseIndicators = [ "license", "licence", "copyright", "author" ]
################################################################################

def findLicense(lines, indicators):
    """Loop over indicators and return line and indicator
       index of first match."""
    for i in range(len(indicators)):
        lineNo = 0
        for l in lines:
            if indicators[i] in l.lower():
                return (lineNo, i)
            lineNo +=1
    return (-1, -1)

def gatherCommentBlock(lines, start, lineComments, blockComments):
    """Gathers the lines before and after lines[start]
       belonging to the same comment block."""
    startLine = lines[start].strip()
    lineCmt = ""
    inBlockComment = True
    for c in lineComments:
        if startLine.startswith(c):
            lineCmt = c
            inBlockComment = False
            break
    commentBlockBegin = start
    commentBlockEnd = start
    if not inBlockComment:
        while (commentBlockBegin > 0
            and lines[commentBlockBegin - 1].strip().startswith(lineCmt)):
            commentBlockBegin -= 1
        while (commentBlockEnd < len(lines) - 1
            and lines[commentBlockEnd + 1].strip().startswith(lineCmt)):
            commentBlockEnd += 1
    else:
        endBlockCmt = ""
        beginBlockCommentFound = False
        for i in range(start - 1, -1, -1):
            curLine = lines[i].strip()
            for (b,e) in blockComments:
                if curLine.startswith(b):
                    commentBlockBegin = i
                    beginBlockCommentFound = True
                    endBlockCmt = e
                    break
                elif curLine.endswith(e):
                    # We can't be inside a block comment!
                    return (-1,-1)
            if beginBlockCommentFound:
                break
        if not beginBlockCommentFound:
            # Something went wrong
            return (-1,-1)
        for i in range(start + 1, len(lines)):
            curLine = lines[i].strip()
            if curLine.endswith(endBlockCmt):
                commentBlockEnd = i
                break
    # grab empty lines before and after
    for i in range(commentBlockBegin - 1,-1,-1):
        if len(lines[i].strip()) > 0:
            commentBlockBegin = i + 1
            break
    for i in range(commentBlockEnd + 1,len(lines)):
        if len(lines[i].strip()) > 0:
            commentBlockEnd = i - 1
            break
    return (commentBlockBegin, commentBlockEnd)

def writeFile(filename, oldLines, beforeLicense, afterLicense, license):
    """Writes lines in oldLines to specified file, replacing all lines
       between beforeLicense and afterLicense with content of license."""
    with open(filename, 'w') as f:
        f.write(''.join(oldLines[:beforeLicense + 1]))
        f.write(''.join(license))
        f.write(''.join(oldLines[afterLicense:]))

def checkFile(filename, lang, indicators, license, insertNewLine):
    """Checks license header for given file using specified language,
       indicators, license header, and newline option."""
    with open(filename, 'r') as f:
        fileLines = f.readlines()
    #
    begin = -1
    ind = indicators[:]
    lic = license[:]
    indicator = -1
    while begin < 0 and len(ind) > 0:
        lineNo, indicator = findLicense(fileLines, ind)
        if lineNo < 0:
            print("No license indicator found.")
            if insertNewLine:
                lic.append("\n")
            writeFile(filename, fileLines, -1, 0, lic)
            return
        begin, end = gatherCommentBlock(fileLines, lineNo,
                commentTokens[lang]['line'], commentTokens[lang]['block'])
        if begin >= 0:
            print("Found license indicator \"{}\" in line {} within comment block:\n>{}"
                    .format(ind[indicator], lineNo, '>'.join(fileLines[begin:end + 1])),end='')
            if insertNewLine and begin > 0:
                lic.insert(0,"\n")
            if insertNewLine and end < len(fileLines) - 1:
                lic.append("\n")
            if fileLines[begin:end + 1] == lic:
                print("License header correct.")
            else:
                print("License headers differ. Replacing it.")
                writeFile(filename, fileLines, begin - 1, end + 1, lic)
            return
        else:
            ind = ind[indicator + 1:]
    #
    print("No valid license indicator found.")
    if insertNewLine:
        lic.append("\n")
    writeFile(filename, fileLines, -1, 0, lic)

def guessLanguage(filename):
    """Tries to guess the language used in given file."""
    for lang, extensions in fileExtensions.items():
        for e in extensions:
            if filename.endswith(e):
                return lang
    with open(filename, 'r') as f:
        firstline = f.readline().lower()
        if firstline.startswith("#!"):
            # recognize shebang
            for lang in fileExtensions.keys():
                if lang in firstline:
                    return lang
            for lang, alias in aliases.items():
                if lang in firstline:
                    return alias
    return ''

def main():
    parser = argparse.ArgumentParser(
            description='Checks and, if necessary, fixes license headers.')
    parser.add_argument('-l', '--language', choices = list(commentTokens.keys()),
            help='disable guessing and assume this language')
    parser.add_argument('-n', '--newline', action="store_true", default=True,
            help='insert an empty line between license header and code')
    parser.add_argument('header_file', metavar='<license header>',
            help='the license header')
    parser.add_argument('src_files', metavar='<file>', nargs='+',
            help='a file to check')
    args = parser.parse_args()
    with open(args.header_file, 'r') as header_file:
        license = header_file.readlines()
    print("Loaded license:\n>{}".format('>'.join(license)),end='')
    for src in args.src_files:
        lang = guessLanguage(src) if args.language is None else args.language
        if len(lang) == 0:
            print("Unable to recognize language used in {}. \
                    Please specify explicitly with -l.".format(src))
            exit(1)
        print("Processing file {} with language {}.".format(src,lang))
        checkFile(src, lang, licenseIndicators, license, args.newline)

if __name__ == "__main__":
    main()
