@echo off
REM Перейти в директорию с файлами
cd /d E:\dev\cats\get_sound

REM Выполнить команду Perl для выполнения sofiactl.pl
perl sofiactl.pl --user admin --pass Lud2704asz --host 192.168.1.41 --port 34567 --command Talk --if lay.pcm
