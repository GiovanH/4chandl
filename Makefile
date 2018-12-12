MODE = c # Console or Windowed



all: 4chan.exe 

clean:
	rm -rv build dist __pycache__ 

%.exe: %.py
	pyinstaller $< -F -$(MODE) -n $@
