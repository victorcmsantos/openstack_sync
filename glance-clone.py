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

#####################################################################################################################################
# credentials should be like bellow
#[keystone_authtoken_origin]
#auth_url = http://keystone.region01.xurupita.nl:5000/v3
#auth_type = password
#project_domain_name = Default
#user_domain_name = Default
#project_name = admin
#username = admin
#password = ADMIN_PASS
#region=region01

# configurations to get information from file
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

# you can use this file or pass other file by "--config-file"
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

# get the credential on origin openstack
sess_origin = session.Session(auth=auth_origin)
keystone_origin = client.Client(session=sess_origin)

# get the list of which federated openstack on origin
idp_manager = service_providers.ServiceProviderManager(keystone_origin)

# the loop to configure all federated openstacks 
for provider in idp_manager.list():

  # now on which federated openstack will get the credentials to start to create/modify resources
  k2kauth = k2k.Keystone2Keystone(auth_origin, provider.id, project_name='admin', project_domain_name='default')
  sess_remote = session.Session(auth=k2kauth)
  keystone_remote = client.Client(session=sess_remote)

  # just a test to see if federation is ok #####################
  # on origin  
#  for projects_origin in keystone_origin.projects.list():
#    print projects_origin.id
#  print 
  # on remote
#  for projects_remote in keystone_remote.projects.list():
#    print projects_remote.id
  
  # glance credentials and endpoints on origin
  glance_origin = glanceclient('2', session=sess_origin)
  # glance credentials and endpoints on remote
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
      # domain_id
      self.domain_id = keystone_remote_domain_id
      for remotes_id_name in keystone_remote_projects:
        if origin_names.project_name == remotes_id_name.name:
          # project_id
          self.project_id = remotes_id_name.id


  class update_remote_metadata:
    def __init__(self, image_id):
      # all metadatas that is not possible to replace
      image_metadata_update = ['updated_at','file','id','size','locations','checksum','created_at','os_hash_value','owner']
      # comparing these metadatas
      for values in image_metadata_update:
        #removing the metadatas that is not possible to replece
        for key in [key for key in images_origin if key == values]: del images_origin[key]
      # doing a loop to create or update all others metadatas  
      for keyclean in images_origin:
        #this transforme the key/value in string "I think"
        att = {keyclean: images_origin[keyclean]}
        glance_remote.images.update(image_id, **att )
      return
  
  # all metadata that is not to remove 
  image_metadata_dont_rm = ['updated_at','file','id','size','locations','checksum','created_at','os_hash_value','owner','status','schema','tags','os_hash_algo','virtual_size','name','container_format','os_hidden','min_ram','disk_format','visibility','protected','min_disk']
  # array that containg the images from remote 
  imgs_remote=[]
  # for to compare if the image exist or not on remote
  for images_remote in glance_remote.images.list():
    # it fell the array if the images on remote
    imgs_remote.append(images_remote.id)
  
  for images_origin in glance_origin.images.list():
    # when the image exists
    if images_origin.id in imgs_remote:
      print "this image exite on remote updating", images_origin.id

      # array that will contain the metadata to remote
      image_md_to_rm_remote=[]
      # geting all information form remote image
      image_md_remote = glance_remote.images.get(images_origin.id)
      # comparing all metadatas from remote against metadata that you can remove
      for keys in image_md_remote:
        # felling the array with metadata that you can remove
        if not keys in image_metadata_dont_rm:
          image_md_to_rm_remote.append(keys)
      # removing all metatadas that is removeble 
      glance_remote.images.update(images_origin.id, remove_props=image_md_to_rm_remote )   
      # recriating/creating all metadatas from origin image
      update_remote_metadata(image_md_remote.id)

    else:
      # creating the image on remote and adding all metadatas
      print "this iamge don't exist on remote", images_origin.id
      # this get the id of domain and project on remote of the respective domain and id on origin "should be the same names"
      remotes = get_remote_ids(images_origin.owner)

      # download the image from origin
      image_file = open(images_origin.id, 'w+')
      for chunk in glance_origin.images.data(images_origin.id):
          image_file.write(chunk)
      
      # creatinf the image on remote as configurations on origin
      glance_image_create_remote = glance_remote.images.create(
        id=images_origin.id,
        disk_format=images_origin.disk_format,
        container_format=images_origin.container_format)
      # uploading the data of this image
      glance_remote.images.upload(glance_image_create_remote.id, open(images_origin.id, 'rb'))
      # changing the owner to respective project on remote
      glance_remote.images.update(glance_image_create_remote.id, owner=remotes.project_id)

      # doing a loop to create or update all others metadatas  
      update_remote_metadata(glance_image_create_remote.id)

