# nano-logging-tools

# Installing nanomsg on Debian

* Get nanomsg from [](http://nanomsg.org/download.html)  
```wget http://download.nanomsg.org/nanomsg-0.5-beta.tar.gz```

* Unpack  
```tar xvzf nanomsg-0.5-beta.tar.gz```

* Configure and make  
```
cd nanomsg-0.5-beta
./configure
make
```

* Install using one of the two options:
    - Create and install a debian package  
    ```
    sudo apt-get install checkinstall; 
    sudo checkinstall -D --pkgname nanomsg --pkgversion 0.5 --pkgrelease 1 --default
    ```
    - Install from source  
    ```sudo make install```

* Update shared library cache  
```sudo ldconfig```


# Installing Python nanomsg library
```sudo pip install nanomsg```
