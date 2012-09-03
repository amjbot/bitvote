SHELL=/bin/bash

restart: tar
	sudo supervisorctl restart all

status:
	sudo supervisorctl status all

stop:
	sudo supervisorctl stop all

tar:
	tar -czf source.tar.gz etc www
	mv -f source.tar.gz www/static/tar/source.tar.gz

reset-database:
	mysql -u root -proot root < etc/schema.sql

tail-log:
	sudo tail -1000 /var/log/supervisor/cell0-stdout*.log

tail-err:
	sudo tail -1000 /var/log/supervisor/cell0-stderr*.log
