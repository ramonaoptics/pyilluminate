%% Ramona Optics C008 Matlab Usage example 
% This sample code shows how to turn on the Green LEDs on the C008-IR board
% Updated July 14, 2021
% By: Ramona Optics Inc

light = serialport( ...
    'COM4', 115200, ...
    'StopBits', 1, ...
    'DataBits', 8, ...
    'Timeout', 1, ...
    'FlowControl', 'none' ...
);
light.configureTerminator('LF');
%%
% This helps clear the state of the board in case it was left in a stuck
% state
light.writeline('reboot')
light.readline()
% it takes about 500 ms for the teensy to reboot
pause(0.5)
light.readline();
%%
light.writeline('version');
light.readline()
light.readline();
%%
light.writeline('sb.max');
light.readline()
light.readline();
%% Unlike the python API, the colors here are between 0 and 2 ^ 16 -1
% sc = setColor
light.writeline('setColor.0.255.0');
light.readline()
light.readline();
%%
light.writeline('fillCheckboard00')
light.readline();
%% 
% xx = clear
light.writeline('xx')
light.readline();
