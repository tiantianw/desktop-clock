' Launch DesktopClock without a console window (source version).
' Double-click this file, or make a shortcut to it.
Dim fso, shell, here
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
here = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = here
shell.Run """C:\ProgramData\Anaconda3\pythonw.exe"" """ & here & "\run.pyw""", 0, False
