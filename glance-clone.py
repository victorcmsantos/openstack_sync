#!/usr/bin/env python
import os
from keystoneauth1.identity import v3
from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient.v3 import client
from glanceclient import Client as glanceclient
from keystoneauth1.identity.v3 import k2k
from keystoneclient.v3.contrib.federation import service_providers

from oslo_config import cfg
from oslo_config import types
CONF = cfg.CONF

keystone_authtoken_origin = cfg.OptGroup(name = "keystone_authtoken_origin", title= "configs for origin glance")

keystone_authtoken_origin_opts=[ 
    cfg.StrOpt('auth_url', default = '', help = ''),
    cfg.StrOpt('auth_type', default = '', help = ''),
    cfg.StrOpt('project_domain_name', default = '', help = ''),
    cfg.StrOpt('user_domain_name', default = '', help = ''),
    cfg.StrOpt('project_name', default = '', help = ''),
    cfg.StrOpt('username', default = '', help = ''),
    cfg.StrOpt('password', default = '', help = ''),
    cfg.StrOpt('region', default = '', help = ''),
]

CONF.register_group(keystone_authtoken_origin)

CONF.register_opts(keystone_authtoken_origin_opts, keystone_authtoken_origin)

CONF(default_config_files=['/etc/glance/glance-clone.conf',])

####################################################################################
auth_origin = v3.Password(
  auth_url=CONF.keystone_authtoken_origin.auth_url,
  username=CONF.keystone_authtoken_origin.username,
  password=CONF.keystone_authtoken_origin.password,
  project_name=CONF.keystone_authtoken_origin.project_name,
  user_domain_name=CONF.keystone_authtoken_origin.user_domain_name,
  project_domain_name=CONF.keystone_authtoken_origin.project_domain_name
)

sess_origin = session.Session(auth=auth_origin)
keystone_origin = client.Client(session=sess_origin)

idp_manager = service_providers.ServiceProviderManager(keystone_origin)
for provider in idp_manager.list():

  k2kauth = k2k.Keystone2Keystone(auth_origin, provider.id, project_name='admin', project_domain_name='default')
  sess_remote = session.Session(auth=k2kauth)
  keystone_remote = client.Client(session=sess_remote)
  
#  ## keystone
#  for projects_origin in keystone_origin.projects.list():
#    print projects_origin.id
#  print 
#  for projects_remote in keystone_remote.projects.list():
#    print projects_remote.id
  
  #### glance
  glance_origin = glanceclient('2', session=sess_origin)
  glance_remote = glanceclient('2', session=sess_remote)
  
  class get_origin_names:
    def __init__(self, ownerid):
      origin_owner = keystone_origin.projects.get(ownerid)
      origin_domain_id = origin_owner.domain_id
      origin_domain_info = keystone_origin.domains.get(origin_domain_id)
      origin_domain_name = origin_domain_info.name
      origin_project_name = origin_owner.name
      self.domain_name = origin_domain_name
      self.project_name = origin_project_name
  
  class get_remote_ids:
    def __init__(self, ownerid):
      projs_remote=[]
      origin_names = get_origin_names(images_origin.owner)
      keystone_remote_domain = keystone_remote.domains.list(name=origin_names.domain_name)
      keystone_remote_domain_id = keystone_remote_domain[0].id
      keystone_remote_projects =  keystone_remote.projects.list(domain=keystone_remote_domain_id)
  #    #domain_id
      self.domain_id = keystone_remote_domain_id
      for remotes_id_name in keystone_remote_projects:
        if origin_names.project_name == remotes_id_name.name:
  #        #project_id
          self.project_id = remotes_id_name.id
  
  imgs_remote=[]
  image_metadata_vals = ['updated_at','file','id','size','locations','checksum','created_at','os_hash_value','owner']
  for images_remote in glance_remote.images.list():
    imgs_remote.append(images_remote.id)
  
  for images_origin in glance_origin.images.list():
    if images_origin.id in imgs_remote:
      ### need to improve, add metadata and others congifuratiosn when the image exists
      print "this image exite on remote", images_origin.id
### not in inverter the keys and what is not on image_metadata_vals remove!!!
#      for values in image_metadata_vals:
#        for key not in [key for key in images_origin if key == values]: del images_origin[key] 
#      for keyclean in images_origin:
#        att = {keyclean: images_origin[keyclean]}
###        print att
#        glance_remote.images.update(glance_image_create_remote.id, **att )   



    else:
      ### need to improve, creating the image on remote, add all metadatas
      print "this iamge don't exist on remote", images_origin.id
      remotes = get_remote_ids(images_origin.owner)

      image_file = open(images_origin.id, 'w+')
      for chunk in glance_origin.images.data(images_origin.id):
          image_file.write(chunk)
        
      glance_image_create_remote = glance_remote.images.create(
        disk_format=images_origin.disk_format,
        container_format=images_origin.container_format)
      glance_remote.images.upload(glance_image_create_remote.id, open(images_origin.id, 'rb'))
      glance_remote.images.update(glance_image_create_remote.id, owner=remotes.project_id)

      for values in image_metadata_vals:
        for key in [key for key in images_origin if key == values]: del images_origin[key] 
      for keyclean in images_origin:
        att = {keyclean: images_origin[keyclean]} 
        glance_remote.images.update(glance_image_create_remote.id, **att )   


