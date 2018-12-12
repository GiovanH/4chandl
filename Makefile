all: 4chan.c.exe 4chan.exe 

clean:
	rm -rv build dist __pycache__ 

4chan.exe: *.py
	pyinstaller $< -F -w

4chan.c.exe: *.py
	pyinstaller $< -F -c -n $@