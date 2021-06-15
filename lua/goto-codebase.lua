local M = {
    conf = {
      width = 120; -- Width of the floating window
      height = 15; -- Height of the floating window
      -- default_mappings = false; -- Bind default mappings
      debug = false; -- Print debug information
      opacity = nil; -- 0-100 opacity level of the floating window where 100 is fully transparent.
      file = nil;
    }
  }

  local logger = {
    debug = function(...)
      if M.conf.debug then
        print("goto-preview:", ...)
      end
    end
  }

  M.setup = function(conf)
    if conf and not vim.tbl_isempty(conf) then
      M.conf = vim.tbl_extend('force', M.conf, conf)

      if M.conf.file then
		-- print(M.conf.file)
        M.open_floating_win(M.conf.file)
      end
    end
  end

  local function tablefind(tab,el)
    for index, value in pairs(tab) do
      if value == el then
        return index
      end
    end
  end

  local windows = {}

  M.open_floating_win = function(file)
    -- local buffer = file
	local buffer_uri = vim.uri_from_fname(file)
	local buffer = vim.uri_to_bufnr(buffer_uri)

    local bufpos = { vim.fn.line(".")-1, vim.fn.col(".")  } -- FOR relative='win'

    local zindex = vim.tbl_isempty(windows) and 1 or #windows+1

    local new_window = vim.api.nvim_open_win(buffer, true, {
      relative='win',
      width=M.conf.width,
      height=M.conf.height,
      border={"↖", "─" ,"┐", "│", "┘", "─", "└", "│"},
      bufpos=bufpos,
	  zindex=zindex, -- TODO: do I need to set this at all?
	  win=vim.api.nvim_get_current_win()
    })


    -- if M.conf.opacity then vim.api.nvim_win_set_option(new_window, "winblend", M.conf.opacity) end
    -- vim.api.nvim_buf_set_option(buffer, 'bufhidden', 'wipe')

    table.insert(windows, new_window)

    logger.debug(vim.inspect({
      windows = windows,
      curr_window = vim.api.nvim_get_current_win(),
      new_window = new_window,
      bufpos = bufpos,
      get_config = vim.api.nvim_win_get_config(new_window),
      get_current_line = vim.api.nvim_get_current_line()
    }))

    -- vim.cmd[[
    --   augroup close_float
    --     au!
    --     au WinClosed * lua require('goto-preview').remove_curr_win()
    --   augroup end
    -- ]]

    -- vim.api.nvim_win_set_cursor(new_window, position)
  end


  M.close_all_win = function()
    for index = #windows, 1, -1 do
      local window = windows[index]
      pcall(vim.api.nvim_win_close, window, true)
    end
  end

  M.remove_curr_win = function()
    local index = tablefind(windows, vim.api.nvim_get_current_win())
    if index then
      table.remove(windows, index)
    end
  end

  return M


