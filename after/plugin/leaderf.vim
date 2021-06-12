" ============================================================================
" File:        leaderf.vim
" Description:
" Author:      Yggdroot <archofortune@gmail.com>
" Website:     https://github.com/Yggdroot
" Note:
" License:     Apache License, Version 2.0
" ============================================================================

" Definition of 'arguments' can be similar as
" https://github.com/Yggdroot/LeaderF/blob/master/autoload/leaderf/Any.vim#L85-L140
let s:extension = {
            \   "name": "codebase",
            \   "help": "navigate the codebase",
            \   "manager_id": "leaderf#CodeBase#managerId",
            \   "arguments": [
            \   ]
            \ }
" In order that `Leaderf marks` is available
call g:LfRegisterPythonExtension(s:extension.name, s:extension)

command! -bar -nargs=0 LeaderfCodeBase Leaderf codebase

" In order to be listed by :LeaderfSelf
call g:LfRegisterSelf("LeaderfMarks", "navigate the marks")