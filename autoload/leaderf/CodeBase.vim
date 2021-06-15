" ============================================================================
" File:        CodeBase.vim
" Description:
" Author:      Yggdroot <archofortune@gmail.com>
" Website:     https://github.com/Yggdroot
" Note:
" License:     Apache License, Version 2.0
" ============================================================================

if leaderf#versionCheck() == 0
    finish
endif

exec g:Lf_py "import vim, sys, os.path"
exec g:Lf_py "cwd = vim.eval('expand(\"<sfile>:p:h\")')"
exec g:Lf_py "sys.path.insert(0, os.path.join(cwd, 'python'))"
exec g:Lf_py "from codeBaseExpl import *"


function! leaderf#CodeBase#Maps()
    nmapclear <buffer>
    nnoremap <buffer> <silent> <CR>          :exec g:Lf_py "codeBaseExplManager.accept()"<CR>
    nnoremap <buffer> <silent> o             :exec g:Lf_py "codeBaseExplManager.accept()"<CR>
    nnoremap <buffer> <silent> <2-LeftMouse> :exec g:Lf_py "codeBaseExplManager.accept()"<CR>
    nnoremap <buffer> <silent> x             :exec g:Lf_py "codeBaseExplManager.accept('h')"<CR>
    nnoremap <buffer> <silent> v             :exec g:Lf_py "codeBaseExplManager.accept('v')"<CR>
    nnoremap <buffer> <silent> t             :exec g:Lf_py "codeBaseExplManager.accept('t')"<CR>
    nnoremap <buffer> <silent> q             :exec g:Lf_py "codeBaseExplManager.quit()"<CR>
    " nnoremap <buffer> <silent> <Esc>         :exec g:Lf_py "codeBaseExplManager.quit()"<CR>
    nnoremap <buffer> <silent> i             :exec g:Lf_py "codeBaseExplManager.input()"<CR>
    nnoremap <buffer> <silent> <Tab>         :exec g:Lf_py "codeBaseExplManager.input()"<CR>
    nnoremap <buffer> <silent> <F1>          :exec g:Lf_py "codeBaseExplManager.toggleHelp()"<CR>
    nnoremap <buffer> <silent> <F5>          :exec g:Lf_py "codeBaseExplManager.refresh()"<CR>
    nnoremap <buffer> <silent> s             :exec g:Lf_py "codeBaseExplManager.addSelections()"<CR>
    nnoremap <buffer> <silent> a             :exec g:Lf_py "codeBaseExplManager.selectAll()"<CR>
    nnoremap <buffer> <silent> c             :exec g:Lf_py "codeBaseExplManager.clearSelections()"<CR>
    nnoremap <buffer> <silent> p             :exec g:Lf_py "codeBaseExplManager._previewResult(True)"<CR>
    nnoremap <buffer> <silent> j             j:exec g:Lf_py "codeBaseExplManager._previewResult(False)"<CR>
    nnoremap <buffer> <silent> k             k:exec g:Lf_py "codeBaseExplManager._previewResult(False)"<CR>
    nnoremap <buffer> <silent> <Up>          <Up>:exec g:Lf_py "codeBaseExplManager._previewResult(False)"<CR>
    nnoremap <buffer> <silent> <Down>        <Down>:exec g:Lf_py "codeBaseExplManager._previewResult(False)"<CR>
    nnoremap <buffer> <silent> <PageUp>      <PageUp>:exec g:Lf_py "codeBaseExplManager._previewResult(False)"<CR>
    nnoremap <buffer> <silent> <PageDown>    <PageDown>:exec g:Lf_py "codeBaseExplManager._previewResult(False)"<CR>
    if has("nvim")
        nnoremap <buffer> <silent> <C-Up>    :exec g:Lf_py "codeBaseExplManager._toUpInPopup()"<CR>
        nnoremap <buffer> <silent> <C-Down>  :exec g:Lf_py "codeBaseExplManager._toDownInPopup()"<CR>
        nnoremap <buffer> <silent> <Esc>     :exec g:Lf_py "codeBaseExplManager._closePreviewPopup()"<CR>
    endif
    if has_key(g:Lf_NormalMap, "File")
        for i in g:Lf_NormalMap["File"]
            exec 'nnoremap <buffer> <silent> '.i[0].' '.i[1]
        endfor
    endif
endfunction

function! leaderf#CodeBase#cleanup()
    call leaderf#LfPy("codeBaseExplManager._beforeExit()")
endfunction

function! leaderf#CodeBase#TimerCallback(id)
    call leaderf#LfPy("codeBaseExplManager._workInIdle(bang=True)")
endfunction

function! leaderf#CodeBase#NormalModeFilter(winid, key) abort
    let key = get(g:Lf_KeyDict, get(g:Lf_KeyMap, a:key, a:key), a:key)

    if key !=# "g"
        call win_execute(a:winid, "let g:Lf_File_is_g_pressed = 0")
    endif

    if key ==# "j" || key ==? "<Down>"
        call win_execute(a:winid, "norm! j")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        "redraw
        exec g:Lf_py "codeBaseExplManager._getInstance().refreshPopupStatusline()"
        exec g:Lf_py "codeBaseExplManager._previewResult(False)"
    elseif key ==# "k" || key ==? "<Up>"
        call win_execute(a:winid, "norm! k")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        "redraw
        exec g:Lf_py "codeBaseExplManager._getInstance().refreshPopupStatusline()"
        exec g:Lf_py "codeBaseExplManager._previewResult(False)"
    elseif key ==? "<PageUp>" || key ==? "<C-B>"
        call win_execute(a:winid, "norm! \<PageUp>")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        exec g:Lf_py "codeBaseExplManager._getInstance().refreshPopupStatusline()"
        exec g:Lf_py "codeBaseExplManager._previewResult(False)"
    elseif key ==? "<PageDown>" || key ==? "<C-F>"
        call win_execute(a:winid, "norm! \<PageDown>")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        exec g:Lf_py "codeBaseExplManager._getInstance().refreshPopupStatusline()"
        exec g:Lf_py "codeBaseExplManager._previewResult(False)"
    elseif key ==# "g"
        if get(g:, "Lf_File_is_g_pressed", 0) == 0
            let g:Lf_File_is_g_pressed = 1
        else
            let g:Lf_File_is_g_pressed = 0
            call win_execute(a:winid, "norm! gg")
            exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
            redraw
        endif
    elseif key ==# "G"
        call win_execute(a:winid, "norm! G")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        redraw
    elseif key ==? "<C-U>"
        call win_execute(a:winid, "norm! \<C-U>")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        redraw
    elseif key ==? "<C-D>"
        call win_execute(a:winid, "norm! \<C-D>")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        redraw
    elseif key ==? "<LeftMouse>"
        if exists("*getmousepos")
            let pos = getmousepos()
            call win_execute(pos.winid, "call cursor([pos.line, pos.column])")
            exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
            redraw
            exec g:Lf_py "codeBaseExplManager._previewResult(False)"
        elseif has('patch-8.1.2266')
            call win_execute(a:winid, "exec v:mouse_lnum")
            call win_execute(a:winid, "exec 'norm!'.v:mouse_col.'|'")
            exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
            redraw
            exec g:Lf_py "codeBaseExplManager._previewResult(False)"
        endif
    elseif key ==? "<ScrollWheelUp>"
        call win_execute(a:winid, "norm! 3k")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        redraw
        exec g:Lf_py "codeBaseExplManager._getInstance().refreshPopupStatusline()"
    elseif key ==? "<ScrollWheelDown>"
        call win_execute(a:winid, "norm! 3j")
        exec g:Lf_py "codeBaseExplManager._cli._buildPopupPrompt()"
        redraw
        exec g:Lf_py "codeBaseExplManager._getInstance().refreshPopupStatusline()"
    elseif key ==# "q" || key ==? "<ESC>"
        exec g:Lf_py "codeBaseExplManager.quit()"
    elseif key ==# "i" || key ==? "<Tab>"
        call leaderf#ResetPopupOptions(a:winid, 'filter', 'leaderf#PopupFilter')
        exec g:Lf_py "codeBaseExplManager.input()"
    elseif key ==# "o" || key ==? "<CR>" || key ==? "<2-LeftMouse>"
        exec g:Lf_py "codeBaseExplManager.accept()"
    elseif key ==# "x"
        exec g:Lf_py "codeBaseExplManager.accept('h')"
    elseif key ==# "v"
        exec g:Lf_py "codeBaseExplManager.accept('v')"
    elseif key ==# "t"
        exec g:Lf_py "codeBaseExplManager.accept('t')"
    elseif key ==# "s"
        exec g:Lf_py "codeBaseExplManager.addSelections()"
    elseif key ==# "a"
        exec g:Lf_py "codeBaseExplManager.selectAll()"
    elseif key ==# "c"
        exec g:Lf_py "codeBaseExplManager.clearSelections()"
    elseif key ==# "p"
        exec g:Lf_py "codeBaseExplManager._previewResult(True)"
    elseif key ==? "<F1>"
        exec g:Lf_py "codeBaseExplManager.toggleHelp()"
    elseif key ==? "<F5>"
        exec g:Lf_py "codeBaseExplManager.refresh()"
    elseif key ==? "<C-Up>"
        exec g:Lf_py "codeBaseExplManager._toUpInPopup()"
    elseif key ==? "<C-Down>"
        exec g:Lf_py "codeBaseExplManager._toDownInPopup()"
    endif

    return 1
endfunction

function! leaderf#CodeBase#managerId()
    " pyxeval() has bug
    if g:Lf_PythonVersion == 2
        return pyeval("id(codeBaseExplManager)")
    else
        return py3eval("id(codeBaseExplManager)")
    endif
endfunction