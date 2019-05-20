# nano-logging-tools

nano-logging-tools use [nanomsg](http://nanomsg.org) to transport messages of various nature over the network.
The tools depend on the presence of the nanomsg library and its python wrapper.

# Building and installing nanomsg on Debian

* Get nanomsg from [](https://github.com/nanomsg/nanomsg/archive/1.0.0.tar.gz)  
```wget https://github.com/nanomsg/nanomsg/archive/1.0.0.tar.gz -O nanomsg-1.0.0.tar.gz```

* Unpack  
```tar xvzf nanomsg-1.0.0.tar.gz```

* Configure and make  
```
cd nanomsg-1.0.0
mkdir build
cd build
cmake ..
cmake --build .
ctest -X Debug .
```

* Install using one of the two options:
    - Create and install a debian package  
    ```
    sudo apt-get install checkinstall;
    sudo checkinstall -D --pkgname libnanomsg --pkgversion 1.0.0 --pkgrelease `date +%Y%m%d` --default
    ```
    - Install from source  
    ```
    sudo cmake --build . --target install
    ```

* Update shared library cache  
```
sudo ldconfig
```

# Installing Python nanomsg library

* Install python-dev
```sudo apt-get install python-dev```

* Install nanomsg C library (would have been done in previous step)
```sudo dpkg -i libnanomsg_YYYYMMDD-1.0.0_armhf.deb```

* Install nanomsg for python
```sudo pip install nanomsg```
