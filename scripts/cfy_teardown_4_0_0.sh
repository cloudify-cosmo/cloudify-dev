#!/bin/bash

function print_line() {

  LINE=$1

  echo
  echo '======================================================================'
  echo $LINE
  echo '======================================================================'
  echo
}


if [ "$1" != "-f" ]; then
  print_line "This action requires additional confirmation. Add the '-f' flag to your command if you are certain this command should be executed."
  exit 1
fi

print_line 'Removing component:  manager-ip-setter'
systemctl stop cloudify-manager-ip-setter
systemctl disable cloudify-manager-ip-setter
rm -rf /usr/lib/systemd/system/cloudify-manager-ip-setter.service
rm -rf /etc/sysconfig/cloudify-manager-ip-setter
rm -rf /opt/manager-ip-setter_NOTICE.txt
rm -rf /etc/logrotate.d/manager-ip-setter
rm -rf /opt/cloudify/manager-ip-setter

print_line 'Removing component:  syncthing'
systemctl stop cloudify-syncthing
systemctl disable cloudify-syncthing
rm -rf /usr/lib/systemd/system/cloudify-syncthing.service
rm -rf /etc/sysconfig/cloudify-syncthing
rm -rf /opt/syncthing_NOTICE.txt
rm -rf /etc/logrotate.d/syncthing
rm -rf /opt/syncthing

print_line 'Removing component:  stage'
systemctl stop cloudify-stage
systemctl disable cloudify-stage
rm -rf /usr/lib/systemd/system/cloudify-stage.service
rm -rf /etc/sysconfig/cloudify-stage
rm -rf /opt/stage_NOTICE.txt
rm -rf /etc/logrotate.d/stage
rm -rf /opt/cloudify-stage
rm -rf /opt/nodejs
rm -rf /var/log/cloudify/stage
userdel --force stage_user
groupdel stage_group

print_line 'Removing component:  logstash'
systemctl stop logstash
systemctl disable logstash
rm -rf /usr/lib/systemd/system/cloudify-logstash.service
rm -rf /etc/sysconfig/cloudify-logstash
rm -rf /opt/logstash_NOTICE.txt
rm -rf /etc/logrotate.d/logstash
yum remove -y logstash
rm -rf /opt/logstash
rm -rf /var/log/cloudify/logstash
rm -rf /etc/systemd/system/logstash.service.d
rm -rf /etc/init.d/logstash
rm -rf /etc/logstash

print_line 'Removing component:  riemann'
systemctl stop riemann
systemctl disable riemann
systemctl stop cloudify-riemann
systemctl disable cloudify-riemann
rm -rf /usr/lib/systemd/system/cloudify-riemann.service
rm -rf /etc/sysconfig/cloudify-riemann
rm -rf /opt/riemann_NOTICE.txt
rm -rf /etc/logrotate.d/riemann
yum remove -y riemann
rm -rf /etc/riemann
rm -rf /var/log/cloudify/riemann
rm -rf /opt/lib/langohr.jar
rm -rf /opt/riemann
userdel --force riemann
groupdel riemann

print_line 'Removing component:  amqpinflux'
systemctl stop cloudify-amqpinflux
systemctl disable cloudify-amqpinflux
rm -rf /usr/lib/systemd/system/cloudify-amqpinflux.service
rm -rf /etc/sysconfig/cloudify-amqpinflux
rm -rf /opt/amqpinflux_NOTICE.txt
rm -rf /etc/logrotate.d/amqpinflux
yum remove -y cloudify-amqp-influx
rm -rf /opt/amqpinflux
userdel --force amqpinflux
groupdel amqpinflux

print_line 'Removing component:  java'
systemctl stop java
systemctl disable java
rm -rf /usr/lib/systemd/system/cloudify-java.service
rm -rf /etc/sysconfig/cloudify-java
rm -rf /opt/java_NOTICE.txt
rm -rf /etc/logrotate.d/java
yum remove -y java
rm -rf /var/log/cloudify/java

print_line 'Removing component:  mgmtworker'
systemctl stop cloudify-mgmtworker
systemctl disable cloudify-mgmtworker
rm -rf /usr/lib/systemd/system/cloudify-mgmtworker.service
rm -rf /etc/sysconfig/cloudify-mgmtworker
rm -rf /opt/mgmtworker_NOTICE.txt
rm -rf /etc/logrotate.d/mgmtworker
yum remove -y cloudify-management-worker
rm -rf /opt/mgmtworker
rm -rf /var/log/cloudify/mgmtworker
userdel --force cfyuser
groupdel cfyuser

print_line 'Removing component:  influxdb'
systemctl stop cloudify-influxdb
systemctl disable cloudify-influxdb
rm -rf /usr/lib/systemd/system/cloudify-influxdb.service
rm -rf /etc/sysconfig/cloudify-influxdb
rm -rf /opt/influxdb_NOTICE.txt
rm -rf /etc/logrotate.d/influxdb
yum remove -y influxdb
rm -rf /opt/influxdb
rm -rf /var/log/cloudify/influxdb
rm -rf /etc/init.d/influxdb
userdel --force influxdb
groupdel influxdb

print_line 'Removing component:  nginx'
systemctl stop nginx
systemctl disable nginx
rm -rf /usr/lib/systemd/system/cloudify-nginx.service
rm -rf /etc/sysconfig/cloudify-nginx
rm -rf /opt/nginx_NOTICE.txt
rm -rf /etc/logrotate.d/nginx
yum remove -y nginx
rm -rf /var/log/cloudify/nginx
rm -rf /etc/systemd/system/nginx.service.d
rm -rf /etc/nginx
rm -rf /var/log/nginx
rm -rf /var/cache/nginx
userdel --force nginx
groupdel nginx

print_line 'Removing component:  restservice'
systemctl stop cloudify-restservice
systemctl disable cloudify-restservice
rm -rf /usr/lib/systemd/system/cloudify-restservice.service
rm -rf /etc/sysconfig/cloudify-restservice
rm -rf /opt/restservice_NOTICE.txt
rm -rf /etc/logrotate.d/restservice
yum remove -y cloudify-rest-service
rm -rf /opt/manager
rm -rf /var/log/cloudify/rest
userdel --force cfyuser
groupdel cfyuser

print_line 'Removing component:  rabbitmq'
systemctl stop cloudify-rabbitmq
systemctl disable cloudify-rabbitmq
systemctl stop rabbitmq-server
systemctl disable rabbitmq-server
rm -rf /usr/lib/systemd/system/cloudify-rabbitmq.service
rm -rf /etc/sysconfig/cloudify-rabbitmq
rm -rf /opt/rabbitmq_NOTICE.txt
rm -rf /etc/logrotate.d/rabbitmq
yum remove -y erlang
rm -rf /etc/rabbitmq
rm -rf /var/log/cloudify/rabbitmq
rm -rf /etc/security/limits.d/rabbitmq.conf
rm -rf /var/lib/rabbitmq
rm -rf /usr/lib/rabbitmq
rm -rf /var/log/rabbitmq
userdel --force rabbitmq
groupdel rabbitmq

print_line 'Removing component:  postgresql'
systemctl stop postgresql-9.5
systemctl disable postgresql-9.5
rm -rf /usr/lib/systemd/system/cloudify-postgresql-9.5.service
rm -rf /etc/sysconfig/cloudify-postgresql-9.5
rm -rf /opt/postgresql_NOTICE.txt
rm -rf /etc/logrotate.d/postgresql-9.5
yum remove -y postgresql95
yum remove -y postgresql95-libs
rm -rf /var/lib/pgsql
rm -rf /usr/pgsql-9.5
rm -rf /var/log/cloudify/postgresql
userdel --force postgres
groupdel postgres

print_line 'Removing component:  consul'
systemctl stop cloudify-consul
systemctl disable cloudify-consul
systemctl stop cloudify-consul-watcher
systemctl disable cloudify-consul-watcher
systemctl stop cloudify-consul-recovery-watcher
systemctl disable cloudify-consul-recovery-watcher
rm -rf /usr/lib/systemd/system/cloudify-consul.service
rm -rf /etc/sysconfig/cloudify-consul
rm -rf /opt/consul_NOTICE.txt
rm -rf /etc/logrotate.d/consul
rm -rf /opt/consul
rm -rf /etc/consul.d

print_line 'Removing cloudify directories...'
rm -rf /opt/cloudify
rm -rf /etc/cloudify
rm -rf /var/log/cloudify

print_line 'Teardown complete!'
exit 0

