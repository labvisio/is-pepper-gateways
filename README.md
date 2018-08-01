
# Pepper Gateways

1. Download the [naoqi python sdk](http://doc.aldebaran.com/2-5/dev/python/install_guide.html)
2. Remeber to correctly export sdk python path, e.g: `export PYTHONPATH=$HOME/pynaoqi-python2.7-2.5.5.5-linux64/lib/python2.7/site-packages`
3. Install other dependencies `pip install --user -r requirements.txt`
4. Start any gateway by running the respective service.py file `python ./camera-gateway/service.py`
5. The gateway parameters are passed via environment variables. 