print('Starting Lua Script')

function send_weight()
  --[It could check if the port is connect (maybe) before writting to it.]
  --[Check units.]
  weight, stability, zero, net = GetWeight()
  --weight = ScaleTrim(weight)
  weight, dev_range, dev_target, lower_lim, upper_lim = Pack(weight)
  CommStr(4,'%w,' .. weight .. '#\n')
  print('weight', weight, 'zero', zero)
end


function keep_port_alive(port)
  --[It could check if the port is connect (maybe) before writting to it.]
  CommStr(port, '%#\n') -- Keep alive
  print('') -- Keep alive
end


function set_display(disp)
  DispClrScr(1)
  if disp == "main" then
    DispStr(1, 1, 1, "  Programs")
    DispStr(1, 2, 1, "  --------")
    DispStr(1, 3, 1, "    [Prog1]: Sends weight on key press.")
    DispStr(1, 4, 1, "    [Prog2]: Always sends weight.")
    DispStr(1, 10, 1, "  Prog 1")
    DispStr(1, 10, 11, "  Prog 2")
    DispStr(1, 10, 21, "  Reload")
  elseif disp == "prog_1" then
    DispStr(1, 1, 1, "  -- Running program 1 --")
    DispStr(1, 2, 1, "    ```Sends weight on key press.'''")
    DispStr(1, 3, 1, "    [send]: Send weight value [kg]")
    DispStr(1, 4, 1, "    [stop]: Stop program 1")
    DispStr(1, 10, 1, "   Send")
    DispStr(1, 10, 11, "   Stop")
  elseif disp == "prog_2" then
    DispStr(1, 1, 1, "  -- Running program 2 --")
    DispStr(1, 2, 1, "    ```Always sends weight.'''")
    DispStr(1, 3, 1, "     [stop]: Stop program 2")
    DispStr(1, 10, 11, "   Stop")
  elseif disp == "reload" then
    DispStr(1, 1, 1, "  -- Restarting Lua Interpreter --")
  end
end



function run_prog_1()
  print('Launching prog 1')
  set_display('prog_1')

  while 1 do
    event, value = NextEvent()
    if event == 'softkey' then
      if value == 1 then
        send_weight()
        DispStr(1,5,1, "  >>>>>>>>>>>>>>> SENT <<<<<<<<<<<<<<<  ")
        sleep(0.4)
        DispStr(1,5,1, "                                        ")
      elseif value == 2 then
        print('Exiting loop')
        break
      end
    else
      keep_port_alive(4)
    end
  end
  print("Exiting program 1")
end


function run_prog_2()
  print('Launching prog 2')

  set_display('prog_2')

  while 1 do
    event, value = NextEvent()
        send_weight()

    if event == 'softkey' then
      if value == 2 then
        print('Exiting loop')
        break
      end
    else
      keep_port_alive(4)
    end
  end
  print("Exiting program 2")
end


function run_main()
  while 1 do
    set_display('main')

    event, value = NextEvent()

    if event ==  "softkey" then
      if value == 1 then
        print('Starting prog 1')
        run_prog_1()

      elseif value == 2 then
        print('Starting prog 2')
        run_prog_2()

      elseif value == 3 then
        print('Restarting Lua Interpreter')
        set_display('reload')
        break

      end

    else
      keep_port_alive(4)
    end
  end
end

run_main()

print('End of Lua Script')