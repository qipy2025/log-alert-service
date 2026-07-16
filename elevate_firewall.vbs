Set UAC = CreateObject("Shell.Application")
UAC.ShellExecute "powershell", "/c netsh advfirewall firewall add rule name=""Log Alert Service 5000"" dir=in action=allow protocol=TCP localport=5000 profile=any", "", "runas", 1
