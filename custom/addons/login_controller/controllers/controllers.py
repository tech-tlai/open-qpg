# -*- coding: utf-8 -*-
# Copyright 2021 Artem Shurshilov

from odoo import http
from odoo.http import request
import werkzeug
from werkzeug.urls import url_encode
from odoo import _, SUPERUSER_ID
import mysql.connector
from odoo.exceptions import ValidationError
import time
import logging


class Login(http.Controller):
   @http.route('/login_employee', type='http', auth='none', methods=['GET'],csrf=False)
   def login_action(self, user_id, schedule_id, api_key, participant_pk=0,view_type='form', db='emis_paper', force='',
                    mod_file=None,
                    **kw):
       # program_starts = time.time()
       logging.info("inside login controller")
       if db and db != request.db:
           raise Exception(_("Could not select database '%s'") % db)

       try:
           uid = request.session.authenticate(request.db, user_id, 'user_sample')
       except:
           print('exception occured')
           admin_login = 'admin'
           admin_password = 'BsDtHUo@24'
           uid = request.session.authenticate(request.db, admin_login, admin_password)
           conn = mysql.connector.connect(host='replica1.cvxfty5zotmt.ap-south-1.rds.amazonaws.com',
                                          password='IIT@sch2022', user='iitm', port=3306, database='tnschools_working')
           cursor = conn.cursor()
           try:
               conn = mysql.connector.connect(host='replica1.cvxfty5zotmt.ap-south-1.rds.amazonaws.com',
                                              password='IIT@sch2022', user='iitm', port=3306,
                                              database='tnschools_working')
               cursor = conn.cursor()
               emis_user_check_query = """select teacher_name,school_key_id,us.user_type,rank from udise_staffreg us inner join
                                                               user_category uc on uc.id=us.user_type where uc.user_type1=0 and teacher_id={};""".format(
                   user_id)
               cursor.execute(emis_user_check_query)
               emis_user_check_query_response = cursor.fetchall()
               # print(emis_user_check_query_response)
               flag = 2
           except:
               # print('Exception occur')
               try:
                   conn = mysql.connector.connect(host='replica1.cvxfty5zotmt.ap-south-1.rds.amazonaws.com',
                                                  password='IIT@sch2022', user='iitm', port=3306,
                                                  database='tnschools_working')
                   cursor = conn.cursor()
                   dept_user_id = '"{}"'.format(user_id)
                   emis_user_check_query = """select emis_username from tnschools_working.emis_userlogin where
                                       emis_username={};""".format(
                       dept_user_id)
                   cursor.execute(emis_user_check_query)
                   emis_user_check_query_response = cursor.fetchall()
                   print(emis_user_check_query_response)
                   flag = 1
               except:
                   pass
           if len(emis_user_check_query_response)==0:
               cursor = conn.cursor()
               emis_user_check_query = """select el.user_id,sscc.school_name  from tnschools_working.emis_login el
                                               left join tnschools_working.students_school_child_count sscc on
                                               el.user_id =sscc.udise_code where el.user_id ={};""".format(user_id)
               # print(emis_user_check_query)
               # print(user_id)
               cursor.execute(emis_user_check_query)
               emis_user_check_query_response = cursor.fetchall()
               # print(emis_user_check_query_response)

           user_create_partner = request.env['res.partner'].sudo().create(
               {'name': emis_user_check_query_response[0][0], 'lang': 'en_US',
                'display_name': emis_user_check_query_response[0][0]})
           # print(user_create_partner)
           user_create_users = request.env['res.users'].sudo().create(
               {'login': user_id, 'password': 'user_sample', 'partner_id': user_create_partner.id})
           group_id = request.env['res.groups'].search([('name', '=', 'Staff')])
           user_group_rel = request._cr.execute("""INSERT INTO public.res_groups_users_rel(gid, uid) VALUES (%s,
                               %s);""" % (group_id.id, user_create_users.id))
           request.env.cr.commit()

           uid = request.session.authenticate(request.db, user_id, 'user_sample')

           ##########Event creation + search###############
       event_id = request.env['schedule.details'].search([('schedule_id', '=', int(schedule_id))])
       if event_id:
           # print('Schedule present')
           pass
       else:
           # print('Schedule create')
           conn = mysql.connector.connect(host='replica1.cvxfty5zotmt.ap-south-1.rds.amazonaws.com',
                                          password='IIT@sch2022', user='iitm', port=3306, database='tnschools_working')
           cursor = conn.cursor()
           schedule_details_query = """select event_title,class_std,class_medium,event_startdate,event_type_id_id,ts.id,is_1_n,class_group,flag1  from tnschools_working.scheduler_scheduling ss
                   inner join teacher_subjects ts on ss.class_subject= ts.subjects
                   where schedule_id={};""".format(
               int(schedule_id))
           cursor.execute(schedule_details_query)
           schedule_details_query_response = cursor.fetchall()
           print(schedule_details_query_response)
           # program_starts = time.time()

           # Search for a 'question.subject' record in the environment using specified criteria.
           # Criteria:
           # 1. ('standard', '=', int(schedule_details_query_response[0][1])):
           #    Match the 'standard' field with the integer value from schedule_details_query_response at index 0, position 1.
           # 2. ('subject_code', '=', int(schedule_details_query_response[0][5])):
           #    Match the 'subject_code' field with the integer value from schedule_details_query_response at index 0, position 5.

           # If a matching 'question.subject' record is found, set subject_id_id to the ID of the first record found.
           # If no matching record is found, set subject_id_id to False.

           subject_id = request.env['question.subject'].search(
               ['&', ('standard', '=', int(schedule_details_query_response[0][1])),
                ('subject_code', '=', int(schedule_details_query_response[0][5]))])
           if subject_id:
               subject_id_id=subject_id[0].id
           else:
               subject_id_id=False



           if not schedule_details_query_response[0][8]:
               schedule_type = schedule_details_query_response[0][4]
           elif int(schedule_details_query_response[0][8]==7):
               schedule_type='3'
           elif int(schedule_details_query_response[0][8]==8):
               schedule_type='4'



           event_id = request.env['schedule.details'].create(
               {'schedule_id': schedule_id, 'event_title': schedule_details_query_response[0][0],
                'class_std': schedule_details_query_response[0][1],
                'medium': schedule_details_query_response[0][2],
                'event_startdate': schedule_details_query_response[0][3],
                'schedule_type': schedule_type,
                'is_1_n': schedule_details_query_response[0][6],
                'flag1': schedule_details_query_response[0][8],
               'schedule_subject': subject_id_id})

       #########Design creation + search #############
       is_1_n = event_id.is_1_n
       # print(is_1_n)
       if is_1_n == 0:
           design_id = request.env['education.exam'].search([('cdac_schedule_id', '=', int(schedule_id))])
       elif is_1_n == 1:
           design_id = request.env['education.exam'].search(['&', ('cdac_schedule_id', '=', int(schedule_id)),
                                                             ('participant_pk', '=', int(participant_pk))])
       # print(design_id)
       if design_id:
           # print(design_id)
           action = '102'  ###102 for server and 89 for localhost
           url = '/web#%s' % url_encode({'id': design_id[0].id, 'action': action, 'view_type': view_type})

       else:

           design_id = request.env['education.exam'].create({'exam_name': event_id[0].event_title,
                                                             'standard_dropdown': str(event_id[0].class_std),
                                                             'medium': str(event_id[0].medium),
                                                             'cdac_schedule_id': schedule_id,
                                                             'exam_type': str(event_id[0].schedule_type),
                                                             'subject': event_id[0].schedule_subject.id,
                                                             'participant_pk': participant_pk})

           action = '102'  ###102 for server and 89 for localhost
           url = '/web#%s' % url_encode({'id': design_id[0].id, 'action': action, 'view_type': view_type})
           # print(url)
       logging.info(url)
       # now = time.time()
       # print(now - program_starts)
       return werkzeug.utils.redirect(url)
