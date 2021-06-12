#!/usr/bin/env python
# -*- coding:utf-8 -*-

import vim
import re
import os
import os.path
import fnmatch
import time
import locale
from functools import wraps
from leaderf.utils import *
from leaderf.explorer import *
from leaderf.manager import *
from leaderf.asyncExecutor import AsyncExecutor
from leaderf.devicons import (
    webDevIconsGetFileTypeSymbol,
    removeDevIcons,
    matchaddDevIconsDefault,
    matchaddDevIconsExact,
    matchaddDevIconsExtension,
)

def showRelativePath(func):
    @wraps(func)
    def deco(*args, **kwargs):
        if lfEval("g:Lf_ShowRelativePath") == '1':
            # os.path.relpath() is too slow!
            dir = lfGetCwd() if args[0]._cmd_work_dir == "" else args[1]
            cwd_length = len(lfEncode(dir))
            if not dir.endswith(os.sep):
                cwd_length += 1
            return [line[cwd_length:] for line in func(*args, **kwargs)]
        else:
            return func(*args, **kwargs)
    return deco

def showDevIcons(func):
    @wraps(func)
    def deco(*args, **kwargs):
        if lfEval("get(g:, 'Lf_ShowDevIcons', 1)") == "1":
            content = func(*args, **kwargs)
            # In case of Windows, line feeds may be included when reading from the cache.
            return [format_line(line.rstrip()) for line in content or []]
        else:
            return func(*args, **kwargs)
    return deco

def format_line(line):
    return webDevIconsGetFileTypeSymbol(line) + line


#*****************************************************
# CodeBaseExplorer
#*****************************************************
class CodeBaseExplorer(Explorer):
    def __init__(self):
        self._cur_dir = ''
        self._content = []
        self._cache_dir = os.path.join(lfEval("g:Lf_CacheDirectory"),
                                       '.LfCache',
                                       'python' + lfEval("g:Lf_PythonVersion"),
                                       'file')
        self._cache_index = os.path.join(self._cache_dir, 'cacheIndex')
        self._external_cmd = None
        self._initCache()
        self._executor = []
        self._no_ignore = None
        self._cmd_work_dir = ""

    def _initCache(self):
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)
        if not os.path.exists(self._cache_index):
            with lfOpen(self._cache_index, 'w', errors='ignore'):
                pass

    def _getFiles(self, dir):
        start_time = time.time()
        wildignore = lfEval("g:Lf_WildIgnore")
        file_list = []
        for dir_path, dirs, files in os.walk(dir, followlinks = False
                if lfEval("g:Lf_FollowLinks") == '0' else True):
            dirs[:] = [i for i in dirs if True not in (fnmatch.fnmatch(i,j)
                       for j in wildignore.get('dir', []))]
            for name in files:
                if True not in (fnmatch.fnmatch(name, j)
                                for j in wildignore.get('file', [])):
                    file_list.append(lfEncode(os.path.join(dir_path,name)))
                if time.time() - start_time > float(
                        lfEval("g:Lf_IndexTimeLimit")):
                    return file_list
        return file_list

    @showDevIcons
    @showRelativePath
    def _getFileList(self, dir):
        dir = dir if dir.endswith(os.sep) else dir + os.sep
        with lfOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            path_length = 0
            target = -1
            for i, line in enumerate(lines):
                path = line.split(None, 2)[2].strip()
                if dir.startswith(path) and len(path) > path_length:
                    path_length = len(path)
                    target = i

            if target != -1:
                lines[target] = re.sub('^\S*',
                                       '%.3f' % time.time(),
                                       lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                with lfOpen(os.path.join(self._cache_dir,
                                         lines[target].split(None, 2)[1]),
                            'r', errors='ignore') as cache_file:
                    if lines[target].split(None, 2)[2].strip() == dir:
                        return cache_file.readlines()
                    else:
                        file_list = [line for line in cache_file.readlines()
                                     if line.startswith(dir)]
                        if file_list == []:
                            file_list = self._getFiles(dir)
                        return file_list
            else:
                start_time = time.time()
                file_list = self._getFiles(dir)
                delta_seconds = time.time() - start_time
                if delta_seconds > float(lfEval("g:Lf_NeedCacheTime")):
                    cache_file_name = ''
                    if len(lines) < int(lfEval("g:Lf_NumberOfCache")):
                        f.seek(0, 2)
                        ts = time.time()
                        line = '%.3f cache_%.3f %s\n' % (ts, ts, dir)
                        f.write(line)
                        cache_file_name = 'cache_%.3f' % ts
                    else:
                        for i, line in enumerate(lines):
                            path = line.split(None, 2)[2].strip()
                            if path.startswith(dir):
                                cache_file_name = line.split(None, 2)[1].strip()
                                line = '%.3f %s %s\n' % (time.time(),
                                        cache_file_name, dir)
                                break
                        if cache_file_name == '':
                            timestamp = lines[0].split(None, 2)[0]
                            oldest = 0
                            for i, line in enumerate(lines):
                                if line.split(None, 2)[0] < timestamp:
                                    timestamp = line.split(None, 2)[0]
                                    oldest = i
                            cache_file_name = lines[oldest].split(None, 2)[1].strip()
                            lines[oldest] = '%.3f %s %s\n' % (time.time(),
                                            cache_file_name, dir)
                        f.seek(0)
                        f.truncate(0)
                        f.writelines(lines)
                    with lfOpen(os.path.join(self._cache_dir, cache_file_name),
                                'w', errors='ignore') as cache_file:
                        for line in file_list:
                            cache_file.write(line + '\n')
                return file_list

    @showDevIcons
    def _readFromFileList(self, files):
        result = []
        for file in files:
            with lfOpen(file, 'r', errors='ignore') as f:
                result += f.readlines()
        return result

    def _refresh(self):
        dir = os.path.abspath(self._cur_dir)
        dir = dir if dir.endswith(os.sep) else dir + os.sep
        with lfOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            path_length = 0
            target = -1
            for i, line in enumerate(lines):
                path = line.split(None, 2)[2].strip()
                if dir.startswith(path) and len(path) > path_length:
                    path_length = len(path)
                    target = i

            if target != -1:
                lines[target] = re.sub('^\S*', '%.3f' % time.time(), lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                cache_file_name = lines[target].split(None, 2)[1]
                file_list = self._getFiles(dir)
                with lfOpen(os.path.join(self._cache_dir, cache_file_name),
                            'w', errors='ignore') as cache_file:
                    for line in file_list:
                        cache_file.write(line + '\n')

    def _exists(self, path, dir):
        """
        return True if `dir` exists in `path` or its ancestor path,
        otherwise return False
        """
        if os.name == 'nt':
            # e.g. C:\\
            root = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
        else:
            root = '/'

        while os.path.abspath(path) != root:
            cur_dir = os.path.join(path, dir)
            if os.path.exists(cur_dir) and os.path.isdir(cur_dir):
                return True
            path = os.path.join(path, "..")

        cur_dir = os.path.join(path, dir)
        if os.path.exists(cur_dir) and os.path.isdir(cur_dir):
            return True

        return False

    def _expandGlob(self, type, glob):
        # is absolute path
        if os.name == 'nt' and re.match(r"^[a-zA-Z]:[/\\]", glob) or glob.startswith('/'):
            if type == "file":
                return glob
            elif type == "dir":
                return os.path.join(glob, '*')
            else:
                return glob
        else:
            if type == "file":
                return "**/" + glob
            elif type == "dir":
                return "**/" + os.path.join(glob, '*')
            else:
                return glob

    def _buildCmd(self, dir, **kwargs):
        if self._cmd_work_dir:
            if os.name == 'nt':
                cd_cmd = 'cd /d "{}" && '.format(dir)
            else:
                cd_cmd = 'cd "{}" && '.format(dir)
        else:
            cd_cmd = ""

        if lfEval("g:Lf_ShowRelativePath") == '1' and self._cmd_work_dir == "":
            dir = os.path.relpath(dir)

        if lfEval("exists('g:Lf_ExternalCommand')") == '1':
            if cd_cmd:
                cmd = cd_cmd + lfEval("g:Lf_ExternalCommand").replace('"%s"', '').replace('%s', '')
            else:
                cmd = lfEval("g:Lf_ExternalCommand") % dir.join('""')
            self._external_cmd = cmd
            return cmd

        if lfEval("g:Lf_UseVersionControlTool") == '1':
            if self._exists(dir, ".git") and lfEval("executable('git')") == '1':
                wildignore = lfEval("g:Lf_WildIgnore")
                if ".git" in wildignore.get("dir", []):
                    wildignore.get("dir", []).remove(".git")
                if ".git" in wildignore.get("file", []):
                    wildignore.get("file", []).remove(".git")
                ignore = ""
                for i in wildignore.get("dir", []):
                    ignore += ' -x "%s"' % i
                for i in wildignore.get("file", []):
                    ignore += ' -x "%s"' % i

                if "--no-ignore" in kwargs.get("arguments", {}):
                    no_ignore = ""
                else:
                    no_ignore = "--exclude-standard"

                if lfEval("get(g:, 'Lf_RecurseSubmodules', 0)") == '1':
                    recurse_submodules = "--recurse-submodules"
                else:
                    recurse_submodules = ""

                if cd_cmd:
                    cmd = cd_cmd + 'git ls-files %s && git ls-files --others %s %s' % (recurse_submodules, no_ignore, ignore)
                else:
                    cmd = 'git ls-files %s "%s" && git ls-files --others %s %s "%s"' % (recurse_submodules, dir, no_ignore, ignore, dir)
                self._external_cmd = cmd
                return cmd
            elif self._exists(dir, ".hg") and lfEval("executable('hg')") == '1':
                wildignore = lfEval("g:Lf_WildIgnore")
                if ".hg" in wildignore.get("dir", []):
                    wildignore.get("dir", []).remove(".hg")
                if ".hg" in wildignore["file"]:
                    wildignore.get("file", []).remove(".hg")
                ignore = ""
                for i in wildignore.get("dir", []):
                    ignore += ' -X "%s"' % self._expandGlob("dir", i)
                for i in wildignore.get("file", []):
                    ignore += ' -X "%s"' % self._expandGlob("file", i)

                if cd_cmd:
                    cmd = cd_cmd + 'hg files %s' % ignore
                else:
                    cmd = 'hg files %s "%s"' % (ignore, dir)
                self._external_cmd = cmd
                return cmd

        if lfEval("exists('g:Lf_DefaultExternalTool')") == '1':
            default_tool = {"rg": 0, "pt": 0, "ag": 0, "find": 0}
            tool = lfEval("g:Lf_DefaultExternalTool")
            if tool and lfEval("executable('%s')" % tool) == '0':
                raise Exception("executable '%s' can not be found!" % tool)
            default_tool[tool] = 1
        else:
            default_tool = {"rg": 1, "pt": 1, "ag": 1, "find": 1}

        if default_tool["rg"] and lfEval("executable('rg')") == '1':
            wildignore = lfEval("g:Lf_WildIgnore")
            if os.name == 'nt': # https://github.com/BurntSushi/ripgrep/issues/500
                color = ""
                ignore = ""
                for i in wildignore.get("dir", []):
                    if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'): # rg does not show hidden files by default
                        ignore += ' -g "!%s"' % i
                for i in wildignore.get("file", []):
                    if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'):
                        ignore += ' -g "!%s"' % i
            else:
                color = "--color never"
                ignore = ""
                for i in wildignore.get("dir", []):
                    if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'):
                        ignore += " -g '!%s'" % i
                for i in wildignore.get("file", []):
                    if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'):
                        ignore += " -g '!%s'" % i

            if lfEval("g:Lf_FollowLinks") == '1':
                followlinks = "-L"
            else:
                followlinks = ""

            if lfEval("g:Lf_ShowHidden") == '0':
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if "--no-ignore" in kwargs.get("arguments", {}):
                no_ignore = "--no-ignore"
            else:
                no_ignore = ""

            if dir == '.':
                cur_dir = ''
            else:
                cur_dir = '"%s"' % dir

            if cd_cmd:
                cmd = cd_cmd + 'rg --no-messages --files %s %s %s %s %s' % (color, ignore, followlinks, show_hidden, no_ignore)
            else:
                cmd = 'rg --no-messages --files %s %s %s %s %s %s' % (color, ignore, followlinks, show_hidden, no_ignore, cur_dir)
        elif default_tool["pt"] and lfEval("executable('pt')") == '1':
            wildignore = lfEval("g:Lf_WildIgnore")
            ignore = ""
            for i in wildignore.get("dir", []):
                if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'): # pt does not show hidden files by default
                    ignore += " --ignore=%s" % i
            for i in wildignore.get("file", []):
                if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'):
                    ignore += " --ignore=%s" % i

            if lfEval("g:Lf_FollowLinks") == '1':
                followlinks = "-f"
            else:
                followlinks = ""

            if lfEval("g:Lf_ShowHidden") == '0':
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if "--no-ignore" in kwargs.get("arguments", {}):
                no_ignore = "-U"
            else:
                no_ignore = ""

            if cd_cmd:
                cmd = cd_cmd + 'pt --nocolor %s %s %s %s -g=""' % (ignore, followlinks, show_hidden, no_ignore)
            else:
                cmd = 'pt --nocolor %s %s %s %s -g="" "%s"' % (ignore, followlinks, show_hidden, no_ignore, dir)
        elif default_tool["ag"] and lfEval("executable('ag')") == '1':
            wildignore = lfEval("g:Lf_WildIgnore")
            ignore = ""
            for i in wildignore.get("dir", []):
                if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'): # ag does not show hidden files by default
                    ignore += ' --ignore "%s"' % i
            for i in wildignore.get("file", []):
                if lfEval("g:Lf_ShowHidden") != '0' or not i.startswith('.'):
                    ignore += ' --ignore "%s"' % i

            if lfEval("g:Lf_FollowLinks") == '1':
                followlinks = "-f"
            else:
                followlinks = ""

            if lfEval("g:Lf_ShowHidden") == '0':
                show_hidden = ""
            else:
                show_hidden = "--hidden"

            if "--no-ignore" in kwargs.get("arguments", {}):
                no_ignore = "-U"
            else:
                no_ignore = ""

            if cd_cmd:
                cmd = cd_cmd + 'ag --nocolor --silent %s %s %s %s -g ""' % (ignore, followlinks, show_hidden, no_ignore)
            else:
                cmd = 'ag --nocolor --silent %s %s %s %s -g "" "%s"' % (ignore, followlinks, show_hidden, no_ignore, dir)
        elif default_tool["find"] and lfEval("executable('find')") == '1' \
                and lfEval("executable('sed')") == '1' and os.name != 'nt':
            wildignore = lfEval("g:Lf_WildIgnore")
            ignore_dir = ""
            for d in wildignore.get("dir", []):
                ignore_dir += '-type d -name "%s" -prune -o ' % d

            ignore_file = ""
            for f in wildignore.get("file", []):
                    ignore_file += '-type f -name "%s" -o ' % f

            if lfEval("g:Lf_FollowLinks") == '1':
                followlinks = "-L"
            else:
                followlinks = ""

            if lfEval("g:Lf_ShowRelativePath") == '1':
                strip = "| sed 's#^\./##'"
            else:
                strip = ""

            if os.name == 'nt':
                redir_err = ""
            else:
                redir_err = " 2>/dev/null"

            if lfEval("g:Lf_ShowHidden") == '0':
                show_hidden = '-name ".*" -prune -o'
            else:
                show_hidden = ""

            if cd_cmd:
                cmd = cd_cmd + 'find %s . -name "." -o %s %s %s -type f -print %s %s' % (followlinks,
                                                                                         ignore_dir,
                                                                                         ignore_file,
                                                                                         show_hidden,
                                                                                         redir_err,
                                                                                         strip)
            else:
                cmd = 'find %s "%s" -name "." -o %s %s %s -type f -print %s %s' % (followlinks,
                                                                                   dir,
                                                                                   ignore_dir,
                                                                                   ignore_file,
                                                                                   show_hidden,
                                                                                   redir_err,
                                                                                   strip)
        else:
            cmd = None

        self._external_cmd = cmd

        return cmd

    @removeDevIcons
    def _writeCache(self, content):
        dir = self._cur_dir if self._cur_dir.endswith(os.sep) else self._cur_dir + os.sep
        with lfOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            target = -1
            for i, line in enumerate(lines):
                if dir == line.split(None, 2)[2].strip():
                    target = i
                    break

            if target != -1:    # already cached
                if time.time() - self._cmd_start_time <= float(lfEval("g:Lf_NeedCacheTime")):
                    os.remove(os.path.join(self._cache_dir, lines[target].split(None, 2)[1]))
                    del lines[target]
                    f.seek(0)
                    f.truncate(0)
                    f.writelines(lines)
                    return

                # update the time
                lines[target] = re.sub('^\S*',
                                       '%.3f' % time.time(),
                                       lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                with lfOpen(os.path.join(self._cache_dir,
                                         lines[target].split(None, 2)[1]),
                            'w', errors='ignore') as cache_file:
                    for line in content:
                        cache_file.write(line + '\n')
            else:
                if time.time() - self._cmd_start_time <= float(lfEval("g:Lf_NeedCacheTime")):
                    return

                cache_file_name = ''
                if len(lines) < int(lfEval("g:Lf_NumberOfCache")):
                    f.seek(0, 2)
                    ts = time.time()
                    # e.g., line = "1496669495.329 cache_1496669495.329 /foo/bar"
                    line = '%.3f cache_%.3f %s\n' % (ts, ts, dir)
                    f.write(line)
                    cache_file_name = 'cache_%.3f' % ts
                else:
                    timestamp = lines[0].split(None, 2)[0]
                    oldest = 0
                    for i, line in enumerate(lines):
                        if line.split(None, 2)[0] < timestamp:
                            timestamp = line.split(None, 2)[0]
                            oldest = i
                    cache_file_name = lines[oldest].split(None, 2)[1].strip()
                    lines[oldest] = '%.3f %s %s\n' % (time.time(), cache_file_name, dir)

                    f.seek(0)
                    f.truncate(0)
                    f.writelines(lines)

                with lfOpen(os.path.join(self._cache_dir, cache_file_name),
                            'w', errors='ignore') as cache_file:
                    for line in content:
                        cache_file.write(line + '\n')

    @showDevIcons
    def _getFilesFromCache(self):
        dir = self._cur_dir if self._cur_dir.endswith(os.sep) else self._cur_dir + os.sep
        with lfOpen(self._cache_index, 'r+', errors='ignore') as f:
            lines = f.readlines()
            target = -1
            for i, line in enumerate(lines):
                if dir == line.split(None, 2)[2].strip():
                    target = i
                    break

            if target != -1:    # already cached
                # update the time
                lines[target] = re.sub('^\S*',
                                       '%.3f' % time.time(),
                                       lines[target])
                f.seek(0)
                f.truncate(0)
                f.writelines(lines)
                with lfOpen(os.path.join(self._cache_dir,
                                         lines[target].split(None, 2)[1]),
                            'r', errors='ignore') as cache_file:
                    file_list = cache_file.readlines()
                    if not file_list: # empty
                        return None

                    if lfEval("g:Lf_ShowRelativePath") == '1':
                        if os.path.isabs(file_list[0]):
                            # os.path.relpath() is too slow!
                            cwd_length = len(lfEncode(dir))
                            if not dir.endswith(os.sep):
                                cwd_length += 1
                            return [line[cwd_length:] for line in file_list]
                        else:
                            return file_list
                    else:
                        if os.path.isabs(file_list[0]):
                            return file_list
                        else:
                            return [os.path.join(lfEncode(dir), file) for file in file_list]
            else:
                return None

    def setContent(self, content):
        self._content = content
        if lfEval("g:Lf_UseCache") == '1':
            self._writeCache(content)

    def getContent(self, *args, **kwargs):
        files = kwargs.get("arguments", {}).get("--file", [])
        if files:
            return self._readFromFileList(files)

        dir = lfGetCwd()

        self._cmd_work_dir = ""
        directory = kwargs.get("arguments", {}).get("directory")
        if directory and directory[0] not in ['""', "''"]:
            dir = directory[0].strip('"').rstrip('\\/')
            if os.path.exists(os.path.expanduser(lfDecode(dir))):
                if lfEval("get(g:, 'Lf_NoChdir', 1)") == '0':
                    lfCmd("silent cd %s" % dir)
                    dir = lfGetCwd()
                else:
                    dir = os.path.abspath(lfDecode(dir))
                    self._cmd_work_dir = dir
            else:
                lfCmd("echohl ErrorMsg | redraw | echon "
                      "'Unknown directory `%s`' | echohl NONE" % dir)
                return None

        no_ignore = kwargs.get("arguments", {}).get("--no-ignore")
        if no_ignore != self._no_ignore:
            self._no_ignore = no_ignore
            arg_changes = True
        else:
            arg_changes = False

        if arg_changes or lfEval("g:Lf_UseMemoryCache") == '0' or dir != self._cur_dir or \
                not self._content:
            self._cur_dir = dir

            cmd = self._buildCmd(dir, **kwargs)
            lfCmd("let g:Lf_Debug_Cmd = '%s'" % escQuote(cmd))

            lfCmd("let g:Lf_FilesFromCache = 0")
            if lfEval("g:Lf_UseCache") == '1' and kwargs.get("refresh", False) == False:
                lfCmd("let g:Lf_FilesFromCache = 1")
                self._content = self._getFilesFromCache()
                if self._content:
                    return self._content

            if cmd:
                executor = AsyncExecutor()
                self._executor.append(executor)
                if cmd.split(None, 1)[0] == "dir":
                    content = executor.execute(cmd, format_line)
                else:
                    if lfEval("get(g:, 'Lf_ShowDevIcons', 1)") == "1":
                        content = executor.execute(cmd, encoding=lfEval("&encoding"), format_line=format_line)
                    else:
                        content = executor.execute(cmd, encoding=lfEval("&encoding"))
                self._cmd_start_time = time.time()
                return content
            else:
                self._content = self._getFileList(dir)

        return self._content

    def getFreshContent(self, *args, **kwargs):
        if self._external_cmd:
            self._content = []
            kwargs["refresh"] = True
            return self.getContent(*args, **kwargs)

        self._refresh()
        self._content = self._getFileList(self._cur_dir)
        return self._content

    def getStlCategory(self):
        return 'File'

    def getStlCurDir(self):
        if self._cmd_work_dir:
            return escQuote(lfEncode(self._cmd_work_dir))
        else:
            return escQuote(lfEncode(lfGetCwd()))

    def supportsMulti(self):
        return True

    def supportsNameOnly(self):
        return True

    def cleanup(self):
        for exe in self._executor:
            exe.killProcess()
        self._executor = []

#*****************************************************
# CodeBaseExplManager
#*****************************************************
class CodeBaseExplManager(Manager):
    def __init__(self):
        super(CodeBaseExplManager, self).__init__()

    def _getExplClass(self):
        return CodeBaseExplorer

    def _defineMaps(self):
        lfCmd("call leaderf#CodeBase#Maps()")

    def _acceptSelection(self, *args, **kwargs):
        if len(args) == 0:
            return
        line = args[0]
        cmd = line.split(None, 1)[0]
        lfCmd("norm! `" + cmd)
        lfCmd("norm! zz")
        lfCmd("setlocal cursorline! | redraw | sleep 100m | setlocal cursorline!")

    def _getDigest(self, line, mode):
        """
        specify what part in the line to be processed and highlighted
        Args:
            mode: 0, 1, 2, return the whole line
        """
        if not line:
            return ''
        return line[1:]

    def _getDigestStartPos(self, line, mode):
        """
        return the start position of the digest returned by _getDigest()
        Args:
            mode: 0, 1, 2, return 1
        """
        return 1

    def _createHelp(self):
        help = []
        help.append('" <CR>/<double-click>/o : execute command under cursor')
        help.append('" x : open file under cursor in a horizontally split window')
        help.append('" v : open file under cursor in a vertically split window')
        help.append('" t : open file under cursor in a new tabpage')
        help.append('" i : switch to input mode')
        help.append('" p : preview the result')
        help.append('" q : quit')
        help.append('" <F1> : toggle this help')
        help.append('" ---------------------------------------------------------')
        return help

    def _afterEnter(self):
        super(CodeBaseExplManager, self)._afterEnter()
        if self._getInstance().getWinPos() == 'popup':
            lfCmd("""call win_execute(%d, 'let matchid = matchadd(''Lf_hl_marksTitle'', ''^mark line .*$'')')"""
                    % self._getInstance().getPopupWinId())
            id = int(lfEval("matchid"))
            self._match_ids.append(id)
            lfCmd("""call win_execute(%d, 'let matchid = matchadd(''Lf_hl_marksLineCol'', ''^\s*\S\+\s\+\zs\d\+\s\+\d\+'')')"""
                    % self._getInstance().getPopupWinId())
            id = int(lfEval("matchid"))
            self._match_ids.append(id)
            lfCmd("""call win_execute(%d, 'let matchid = matchadd(''Lf_hl_marksText'', ''^\s*\S\+\s\+\d\+\s\+\d\+\s*\zs.*$'')')"""
                    % self._getInstance().getPopupWinId())
            id = int(lfEval("matchid"))
            self._match_ids.append(id)
        else:
            id = int(lfEval('''matchadd('Lf_hl_marksTitle', '^mark line .*$')'''))
            self._match_ids.append(id)
            id = int(lfEval('''matchadd('Lf_hl_marksLineCol', '^\s*\S\+\s\+\zs\d\+\s\+\d\+')'''))
            self._match_ids.append(id)
            id = int(lfEval('''matchadd('Lf_hl_marksText', '^\s*\S\+\s\+\d\+\s\+\d\+\s*\zs.*$')'''))
            self._match_ids.append(id)

    def _beforeExit(self):
        super(CodeBaseExplManager, self)._beforeExit()

    def _previewInPopup(self, *args, **kwargs):
        if len(args) == 0:
            return

        line = args[0]
        cmd = "silent! norm! `" + line.split(None, 1)[0]

        saved_eventignore = vim.options['eventignore']
        vim.options['eventignore'] = 'BufWinEnter'
        try:
            self._createPopupPreview("", self._getInstance().getOriginalPos()[2].number, 0, jump_cmd=cmd)
        finally:
            vim.options['eventignore'] = saved_eventignore

    def _accept(self, file, mode, *args, **kwargs):
        if file:
            if self._getExplorer().getStlCategory() != "Jumps":
                lfCmd("norm! m'")
            
            print(file)

            if mode == '':
                pass
            elif mode == 'h':
                lfCmd("split")
            elif mode == 'v':
                lfCmd("bel vsplit")

            kwargs["mode"] = mode
            tabpage_count = len(vim.tabpages)
            self._acceptSelection(file, *args, **kwargs)
            for k, v in self._cursorline_dict.items():
                if k.valid:
                    k.options["cursorline"] = v
            self._cursorline_dict.clear()
            self._issue_422_set_option()
            if mode == 't' and len(vim.tabpages) > tabpage_count:
                tab_pos = int(lfEval("g:Lf_TabpagePosition"))
                if tab_pos == 0:
                    lfCmd("tabm 0")
                elif tab_pos == 1:
                    lfCmd("tabm -1")
                elif tab_pos == 3:
                    lfCmd("tabm")

#*****************************************************
# CodeBaseExplManager is a singleton
#*****************************************************
codeBaseExplManager = CodeBaseExplManager()

__all__ = ['codeBaseExplManager']