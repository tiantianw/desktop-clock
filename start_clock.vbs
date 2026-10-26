' Launch DesktopClock without a console window (source version).
' Double-click this file, or make a shortcut to it.
Dim fso, shell, here, exe
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
here = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = here

' Prefer a virtualenv inside the project, otherwise fall back to pythonw on PATH.
If fso.FileExists(here & "\.venv\Scripts\pythonw.exe") Then
    exe = here & "\.venv\Scripts\pythonw.exe"
ElseIf fso.FileExists(here & "\.venvbuild\Scripts\pythonw.exe") Then
    exe = here & "\.venvbuild\Scripts\pythonw.exe"
Else
    exe = "pythonw.exe"
End If

On Error Resume Next
shell.Run """" & exe & """ """ & here & "\run.pyw""", 0, False
If Err.Number <> 0 Then
    MsgBox "pythonw.exe not found." & vbCrLf & vbCrLf & _
           "Install Python 3.9+ and tick ""Add Python to PATH"", or create a .venv in this folder:" & vbCrLf & _
           "    python -m venv .venv" & vbCrLf & _
           "    .venv\Scripts\pip install -r requirements.txt", _
           vbExclamation, "DesktopClock"
End If
