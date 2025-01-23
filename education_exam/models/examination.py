# -*- coding: utf-8 -*-
###############################################################################
#    A part of Educational ERP Project <https://www.educationalerp.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2020-TODAY Cybrosys Technologies (<https://www.cybrosys.com>)
#    Author: Hajaj Roshan (hajaj@cybrosys.in)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from odoo import tools
import random
# import mysql.connector
import re
import json
import werkzeug
from werkzeug.urls import url_encode
import time
import requests
from bs4 import BeautifulSoup

# import pyautogui

_logger = logging.getLogger(__name__)


class EducationExam(models.Model):
    _name = 'education.exam'
    _description = 'Education Exam'
    # _inherit = ['mail.thread', 'mail.activity.mixin']

    # exam_name = fields.Char(string='Exam Name', default='New')
    # description = fields.Char(string='Description', default='Description')
    _rec_name = 'reference'
    # name = fields.Char(string='Name', default='New')
    reference = fields.Char(string='Design ID', required=True, copy=False, readonly=True, default=lambda self: _('New'))

    exam_name = fields.Char(string='Event Name', store=True, placeholder='New',required='True')
    description = fields.Char(string='Design Paper Description', placeholder='Design Paper Description')

    subject_line = fields.One2many('education.subject.line', 'exam_id', string='Subjects')

    question_line = fields.One2many('question.paper', 'exam_id', string='Questions')

    selected_question_line = fields.One2many('selected.question.paper', 'sel_exam_id', string='Selected Questions')
    ##Question Set
    question_set = fields.One2many('selected.question.set', 'set_id', string='Question Set')
    # Question set count
    question_set_count = fields.One2many('selected.question.set', 'set_id', string='Question Set')
    # Paper design
    paper_design = fields.One2many('question.paper.design', 'design_id', string='Paper Design')
    question_set_count_view = fields.One2many('question.set.count', 'set_count_id', string='Question set count')
    question_chapter = fields.One2many('question.subject.chapter', 'set_id', string='Chapter')

    state = fields.Selection([('draft', 'Draft'), ('close', 'Closed'), ('cancel', 'Canceled')], default='draft')

    create_date = fields.Datetime(string='Created Date')

    # subject = fields.Many2one('subject.master', string='Subject*')
    subject = fields.Many2one(
        'subject.master.table',
        string='Subject*',
        domain="[('smt_standard', '=', standard_dropdown), ('smt_medium_code', '=', medium)]"
    )
    subject_domain = fields.Char(compute="_compute_subject_domain", readonly=True, store=False)
    subject_list = fields.One2many('question.subject', 'design_id', string='Subject')

    group_code = fields.Many2one('group.code', string='Stream*')
    group_code_details = fields.One2many('group.code', 'design_id', string='Stream*')

    # medium = fields.Selection(
    #     [('16', 'Tamil'), ('19', 'English'), ('5', 'Kannada'), ('8', 'Malayalam'),
    #      ('17', 'Telugu'), ('18', 'Urdu')], string='Medium*', default='19')
    medium = fields.Selection(
        [('16', 'Tamil'),('19', 'English')], string='Medium*', required=True, default='19')
    # medium = fields.Many2one('medium.master', string='Medium*', required=True)

    standard = fields.Many2one('question.standard', string='Standard*')
    standard_dropdown = fields.Selection(
        [('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12')],
        string='Standard*', required=True, default='11')
    term_id = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('4', 'All')], string='Term', default='3')
    chapter = fields.Many2one('question.subject.chapter', string='Chapter*')
    exam_type = fields.Selection([('1', 'Descriptive'), ('2', 'MCQ'), ('3', 'JEE'), ('4', 'NEET')], string='Event Type',
                                 default='2')

    cdac_user = fields.Integer(string='CDAC user', store=True)
    cdac_schedule_id = fields.Integer(string='CDAC Schedule ID', store=True)

    # schedule_id = fields.Integer(string='QP Schedule ID', store=True, default=None)
    schedule_id= fields.Char(
        string='Schedule ID', required=True, copy=False, readonly=True,
        default=lambda self: _('New')
    )

    chapter_list = fields.One2many('chapter.list', 'set_id', string='Chapter')
    topic_list = fields.One2many('topic.list', 'set_id', string='Topic')

    chapter_dropdown = fields.Many2one('chapter.list', string='Chapter')
    chapter_dropdown_domain = fields.Char(compute="_compute_chapter_dropdown_domain", readonly=True, store=False)

    topic_dropdown = fields.Many2one('topic.list', string='Topic')
    topic_dropdown_domain = fields.Char(compute="_compute_topic_dropdown_domain", readonly=True, store=False)

    selection_criteria = fields.Selection([('1', 'Chapter'), ('2', 'Topic')], string='Criteria',
                                          default='1')
    question_list = fields.One2many('question.list', 'set_id', string='Question')
    school_id = fields.Integer('School ID')
    participant_pk = fields.Integer('Participant row ID')
    class_section = fields.Char('Class Section')

    # _sql_constraints = [
    #     ('unique_schedule_id', 'unique(schedule_id)', 'The QP Schedule ID must be unique.')
    # ]
    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('design.number.series') or _('New')

        if vals.get('schedule_id', _('New')) == _('New'):
            vals['schedule_id'] = self.env['ir.sequence'].next_by_code('schedule.code') or _('New')

        res = super(EducationExam, self).create(vals)
        res.state = 'draft'
        return res

    # This method calculates the 'subject_domain' based on 'standard_dropdown', 'group_code', and 'exam_type'.
    # If 'standard_dropdown' is 11 or 12, the 'stream' in the domain depends on 'group_code.group_code_id' for 'exam_type' 2,
    # or it's set to [7] for 'exam_type' 3 and [8] for 'exam_type' 4.
    # If 'standard_dropdown' is not 11 or 12, only 'standard' is considered in the domain.

    # @api.depends('standard_dropdown', 'group_code')
    # def _compute_subject_domain(self):
    #     for rec in self:
    #         if int(self.standard_dropdown) == 11 or int(self.standard_dropdown) == 12:
    #             if int(self.exam_type) == 2:
    #                 rec.subject_domain = json.dumps([('standard', '=', int(self.standard_dropdown)),
    #                                                  ('stream', 'in', ['NA', self.group_code.group_code_id])])
    #
    #             elif int(self.exam_type) == 3:
    #                 rec.subject_domain = json.dumps([('standard', '=', int(self.standard_dropdown)),
    #                                                  ('stream', 'in', [7])])
    #             elif int(self.exam_type) == 4:
    #                 rec.subject_domain = json.dumps([('standard', '=', int(self.standard_dropdown)),
    #                                                  ('stream', 'in', [8])])
    #         else:
    #             rec.subject_domain = json.dumps(
    #                 [('standard', '=', int(self.standard_dropdown))])

    # @api.onchange('standard_dropdown','group_code')
    # def onchange_partner_id(self):
    #     # for rec in self:
    #     #     return {'domain': {'subject': [('standard', '=', rec.standard_dropdown)]}}
    #     for rec in self:
    #         if int(self.standard_dropdown) == 11 or int(self.standard_dropdown) == 12:
    #             return {'domain': {'subject': [('standard', '=', rec.standard_dropdown),('stream', 'in', ['NA', self.group_code.group_code_id])]}}
    #         else:
    #             return {'domain': {'subject': [('standard', '=', rec.standard_dropdown)]}}

    @api.depends('standard_dropdown', 'medium', 'term_id', 'subject')
    def _compute_chapter_dropdown_domain(self):
        for rec in self:
            if int(self.standard_dropdown) > 4:
                rec.chapter_dropdown_domain = json.dumps(
                    [('cl_medium_id', '=', int(self.medium)), ('cl_standard', '=', int(self.standard_dropdown)),
                     ('cl_subject_id', '=', int(self.subject.smt_subject_code))])
                print(rec.chapter_dropdown_domain)
            # else:
            #     rec.chapter_dropdown_domain = json.dumps(
            #         [('cl_medium_id', '=', int(self.medium)), ('cl_standard', '=', int(self.standard_dropdown)),
            #          ('cl_subject_id', '=', int(self.subject.subject_code)), ('cl_term_id', '=', int(self.term_id))])

    @api.depends('chapter_dropdown', 'medium', 'term_id', 'subject')
    def _compute_topic_dropdown_domain(self):
        for rec in self:
            rec.topic_dropdown_domain = json.dumps(
                [('tl_chapter_idx', '=', int(self.chapter_dropdown.cl_chapter_idx))])

    def pull_data(self):
        self._cr.execute("""DELETE FROM public.chapter_list;""")
        self._cr.execute("""DELETE FROM public.topic_list;""")
        chapter_list_query = ("""select distinct(chapter_unique_id),chapter_name,chapter_id,medium_id,class_studying_id,subject_id,term_id from
                            tnschools_working.schoolnew_taxonomy where class_studying_id >4;""")
        conn = mysql.connector.connect(host='',
                                       password='', user='', port=3306, database='tnschools_working')
        cursor = conn.cursor()
        cursor.execute(chapter_list_query)
        chapter_list_query_response = cursor.fetchall()

        for rec in chapter_list_query_response:
            chapter_id = self.env['chapter.list'].create(
                {"cl_chapter_idx": rec[0], "cl_chapter_name": rec[1], "cl_chapter_id": rec[2],
                 "cl_medium_id": rec[3],
                 "cl_standard": rec[4], "cl_subject_id": rec[5], "cl_term_id": rec[6]})

        topic_list_query = ("""select distinct(topic_unique_id),topic_name,chapter_unique_id from
                                tnschools_working.schoolnew_taxonomy where class_studying_id >4;""")
        cursor = conn.cursor()
        cursor.execute(topic_list_query)
        topic_list_query_response = cursor.fetchall()

        for rec in topic_list_query_response:
            topic_id = self.env['topic.list'].create(
                {"tl_topic_idx": rec[0], "tl_topic_name": rec[1], "tl_chapter_idx": rec[2]})

        return

    def save_details(self):
        # self._cr.execute("""DELETE FROM public.group_code;""")

        stream_query = (
            "select distinct(Group_code),Group_name from tnschools_working.11th_student_details_view where Group_code>2500 and Group_code<3000;")
        conn = mysql.connector.connect(host='',
                                       password='', user='', port=3306, database='tnschools_working')
        cursor = conn.cursor()
        cursor.execute(stream_query)
        stream_query_response = cursor.fetchall()

        for rec in stream_query_response:
            stream = self.env['group.code'].create({"group_code_id": rec[0], 'group_name': rec[1]})

        # self._cr.execute("""DELETE FROM public.question_subject;""")
        subject_query = ("""select standard,stream,school_standard_mapping.subjects,teacher_subjects.subjects from tnschools_working.school_standard_mapping inner join tnschools_working.teacher_subjects on
        school_standard_mapping.subjects=teacher_subjects.id;""")
        conn = mysql.connector.connect(host='',
                                       password='', user='', port=3306, database='tnschools_working')
        cursor = conn.cursor()
        cursor.execute(subject_query)
        subject_query_response = cursor.fetchall()
        for rec in subject_query_response:
            subject = self.env['question.subject'].create(
                {"standard": rec[0], "stream": rec[1], "subject_code": rec[2], "subject_name": rec[3]})
        return

    def save_jn(self):
        subject_code_l = [3, 22, 13, 152, 153]
        subject_name_l = ["Mathematics", "Physics", "Chemistry", "Bio-Botony", "Bio-Zoology"]
        for std in (11, 12):
            for i in range(len(subject_name_l)):
                # print(std,subject_code_l[i],subject_name_l[i])
                subject = self.env['question.subject'].create(
                    {"standard": std, "stream": 'jn', "subject_code": subject_code_l[i],
                     "subject_name": subject_name_l[i]})
        return

    def close_session(self):
        # print('Button pressed')
        action = self.env.ref('education_exam.action_close_session').read()[0]
        return action

    def name_get(self):
        result = []
        for rec in self:
            name = str(rec.reference) + '-' + str(rec.exam_name)
            result.append((rec.id, name))
        return result

    @api.onchange('class_division_hider')
    def onchange_class_division_hider(self):
        self.school_class_division_wise = 'school'

    def close_exam(self):
        self.state = 'close'

    def cancel_exam(self):
        self.state = 'cancel'

    def confirm_exam(self):
        if self.state != 'close':
            count = 0
            subjectName = []
            subject_id = []
            for rec in self.question_set_count_view:
                count = count + 1
                if rec.qc_subject_id.smt_subject_code in subject_id:
                    pass
                else:
                    subjectName.append(rec.qc_subject_id.smt_subject_name)
                    subject_id.append(rec.qc_subject_id.smt_subject_code)
            subjectConcat = ",".join([str(item) for item in subjectName])
            # print("subjectconcat", subjectConcat)
            if count == 0:
                raise UserError('Create atleast 1 group')
            name = str(self.exam_name) + '_standard_' + str(self.standard.standard_id) + '_year_'
            if int(self.exam_type) == 2:
                for rec in self.question_set_count_view:
                    if rec.questions_insert > rec.set_count:
                        raise UserError('Please enter less question count to Questions to insert')
                    elif rec.questions_insert < 1:
                        raise UserError('Please  enter values greater than 0')
            self.state = 'close'
        else:
            subjectConcat = False
            pass

        return subjectConcat

    def select_all(self):
        for line in self.question_list:
            line.checkbox = True

    def deselect_all(self):
        for line in self.question_list:
            line.checkbox = False

    def navigate_version(self):
        subjectConcat = self.confirm_exam()
        print("test", subjectConcat)
        version = self.env['version.master'].search([('cvm_design_id', '=', self.id)])
        if version:
            pass
        else:
            for rec in self.question_list:
                rec.unlink()
            try:
                # if self.participant_pk == 0:
                #     is_1_n = 0
                # else:
                #     is_1_n = 1
                # if self.exam_type == '3':
                #     num_questions_jn = 30
                #     exam_type_value = 3
                #     total_time = 180
                # elif self.exam_type == '4':
                #     num_questions_jn = 45
                #     exam_type_value = 4
                #     total_time = 200
                # else:
                num_questions_jn = 0
                exam_type_value = 2
                total_time = 60

                # schedule_id = self.env['schedule.details'].search([('schedule_id', '=', self.cdac_schedule_id)])
                # schedule_id = 123
                is_1_n = 1

                version = self.env['version.master'].create(
                    {'cvm_design_id': self.id, "cvm_is_1_n": is_1_n, "cvm_subjects": subjectConcat,
                     "cvm_total_questions_jn": num_questions_jn, "cvm_exam_type": exam_type_value,
                      'cvm_total_time': total_time})

            except Exception as exc:
                raise UserError("No event details are attached to current design")
            result = self.env['question.set.count'].search(
                [('set_count_id', '=', self.id)])
            count = 0
            # print(type(result))
            for rec in result:
                count = count + rec.questions_insert
                summary = self.env['version.set.summary'].create(
                    {"cvs_set_no": rec.set_number, "cvs_av_qs": rec.set_count,
                     "cvs_in_qs": rec.questions_insert,
                     "cvs_desc": rec.set_description,
                     "cvs_design_version_id": version[0].id,
                     "cvs_sec": rec.setsection.setsection_id,
                     "cvs_chapter_id": rec.qc_chapter_id,
                     "cvs_difficulty": rec.qc_difficulty,
                     "cvs_subject_id": rec.qc_subject_id.smt_subject_code,
                     "cvs_subject_name": rec.qc_subject_id.smt_subject_name,
                     "cvs_standard": rec.qc_standard})  # JEENEET

            if count > 90:
                raise UserError("Maximum 90 questions allowed!")

        context = dict(self.env.context)
        context['form_view_initial_mode'] = 'edit'
        res = {
            'res_model': 'version.master',
            'res_id': version[0].id,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'context': context
        }
        return res

    # Question deletion
    def question_deletion(self):
        id = self.id
        for rec in self.question_set:
            if rec.checkbox:
                rec.unlink()
        self._cr.execute(
            """Select count(q_id) FROM public.selected_question_set where set_id=%s group by set_no order by set_no""" % (
                self.id))
        result = self._cr.fetchall()

        i = 0
        for rec in self.question_set_count_view:
            update_id = rec._origin.id
            update_list = (1, update_id, {"set_count": result[i][0], })
            self.env['education.exam'].browse(self.id).write({'question_set_count_view': [update_list]})
            i = i + 1

    def set_deletion(self):
        set_list = {}
        set_summary_update = []
        count = 1
        flag = 0
        for line in self.question_set_count_view:
            if line.checkbox == True:
                flag = 1
        if flag == 0:
            raise UserError('Please select group.')
        for line in self.question_set_count_view:
            if line.checkbox == True:
                result = self.env['selected.question.set'].search(
                    ['&', ('set_no', '=', line.set_number), ('set_id', '=', self.id)])

                result.unlink()
                line.unlink()
            else:
                set_list[line.set_number] = count
                set_summary_update.append((1, line.id, {"set_number": count, }))
                set_questions_update = []
                for rec in self.question_set:
                    if rec.set_no == line.set_number:
                        set_questions_update.append((1, rec.id, {"set_no": count, }))
                count = count + 1
                self.env['education.exam'].browse(self.id).write(
                    {'question_set': set_questions_update})

        self.env['education.exam'].browse(self.id).write({'question_set_count_view': set_summary_update})
        return

    ##########################################Descriptive##############################################################################
    def create_desc(self):
        return

    ##########################################MCQ####################################################################
    def search_mcq(self):
        for rec in self.question_list:
            rec.unlink()
        # print('medium', self.medium)
        # print('standard_dropdown', self.standard_dropdown)
        # print('subject', self.subject.subject_name)
        # print('exam_type', self.exam_type)
        # print(int(self.medium), int(self.standard_dropdown), self.subject.subject_name)
        # prgram_start = time.time()
        ############# topic dropdown ############################
        if self.selection_criteria == '2':
            mcq_search_qry = """
                       SELECT 
                            smt.smt_subject_name,
                            stm.stm_chapter_name,
                            stm.stm_topic_name,
                            COUNT(stm.stm_subject_id),
                            stm.stm_chapter_code,
                            stm.stm_topic_code
                        FROM question_master_table AS qmt
                        JOIN subject_taxonomy_master AS stm
                            ON qmt.qmt_taxonomy_id = stm.id
                        JOIN subject_master_table AS smt
                            ON stm.stm_subject_id = smt.id
                        WHERE smt.smt_medium_code = %s AND smt.smt_standard = %s AND smt.smt_subject_name = %s and stm.stm_chapter_name = %s
                        GROUP BY  smt.smt_subject_name, stm.stm_chapter_name, stm.stm_subject_id, stm.stm_topic_name,stm.stm_topic_code,stm.stm_chapter_code
                    """
            # Execute the query with parameters
            try:
                self.env.cr.execute(mcq_search_qry, (int(self.medium), int(self.standard_dropdown), self.subject.smt_subject_name, self.chapter_dropdown.cl_chapter_name))
            except:
                raise UserError("Database is not responding please try after sometime.")

            # Fetch and print the results
            query_response = self.env.cr.fetchall()
            if len(query_response) == 0:
                raise UserError('Sorry, there are no questions available for the selected subject at the moment. '
                                            'Kindly choose another subject.')
            details_list=[]
            unique_chapters = set()
            for rec in query_response:
                details_list.append((0, 0,
                                                 {"ql_criteria_name": 'Topic' if self.selection_criteria == '2' else '',
                                                  "ql_name": rec[2],
                                                  "ql_q_count": rec[3],
                                                  "ql_chapter": rec[1],
                                                  "ql_chapter_idx_id": rec[4],
                                                  "ql_idx_id" : rec[5],
                                                  "ql_topic_idx_id": rec[5],
                                                  'ql_criteria':2
                                                  }))

            self.env['education.exam'].browse(self._origin.id).write({'question_list': details_list})
        ############# chpater dropdown ############################
        if self.selection_criteria == '1':
            mcq_search_qry = """
                        SELECT 
                            smt.smt_subject_name, 
                            stm.stm_chapter_name, 
                            COUNT(stm.stm_subject_id),
                            stm.stm_chapter_code
                        FROM question_master_table AS qmt
                        JOIN subject_taxonomy_master AS stm
                            ON qmt.qmt_taxonomy_id = stm.id
                        JOIN subject_master_table AS smt
                            ON stm.stm_subject_id = smt.id
                        WHERE smt.smt_medium_code = %s AND smt.smt_standard = %s AND smt.smt_subject_name = %s
                        GROUP BY  smt.smt_subject_name, stm.stm_chapter_name, stm.stm_subject_id,stm.stm_chapter_code
                    """
            # Execute the query with parameters
            try:
                self.env.cr.execute(mcq_search_qry, (int(self.medium), int(self.standard_dropdown), self.subject.smt_subject_name))
            except:
                raise UserError("Database is not responding please try after sometime.")

            # Fetch and print the results
            query_response = self.env.cr.fetchall()
            if len(query_response) == 0:
                raise UserError('Sorry, there are no questions available for the selected subject at the moment. '
                                            'Kindly choose another subject.')
            details_list=[]
            unique_chapters = set()
            for rec in query_response:
                details_list.append((0, 0,
                                                 {"ql_criteria_name": 'Chapter' if self.selection_criteria == '1' else '',
                                                  "ql_name": rec[1],
                                                  "ql_q_count": rec[2],
                                                  "ql_idx_id": rec[3],
                                                  'ql_criteria': 1
                                                  }))

            self.env['education.exam'].browse(self._origin.id).write({'question_list': details_list})

        # return query_response


    # def search_mcq(self):
    #     # prgram_start = time.time()
    #     for rec in self.question_list:
    #         rec.unlink()
    #
    #     medium = int(self.medium)
    #     standard = int(self.standard_dropdown)
    #     subject = int(self.subject.subject_code)
    #     term = int(self.term_id)
    #     if subject == 48:
    #         medium = 16
    #     elif subject == 46:
    #         medium = 19
    #     else:
    #         pass
    #
    #     conn = mysql.connector.connect(host='',
    #                                    password='', user='', port=3306, database='tnschools_working')
    #     cursor = conn.cursor()
    #     if self.selection_criteria == '1':
    #         if standard < 8:
    #             q_type = (1, 2)
    #             dl_code = 'S15'
    #         elif standard == 8:
    #             q_type = (1, 2)
    #             term = 4
    #             dl_code = 'S18'
    #         elif standard > 8:
    #             q_type = (1, 100)
    #             term = 4
    #             dl_code = 'S19'
    #
    #         chapter_query = """select ed.chapter_unique_id,chapter_name,count(distinct(ed.q_id)) from tnschools_working.exams_quest_detail ed inner join
    #                             tnschools_working.exams_quest_bank eb on ed.q_id=eb.q_id inner join
    #                             tnschools_working.schoolnew_taxonomy st on st.taxonomy_id=ed.taxonomy_id
    #                             where q_type in {} and q_format in (2,3,4) and eb.created_date>'2022-10-10' and status=4 and assessment_status=1
    #                             and medium_id={} and class_studying_id={} and subject_id={} and term_id={} and ed.chapter_unique_id is not null
    #                              group by ed.chapter_unique_id;""".format(
    #             str(q_type), medium, standard, subject, term)
    #         try:
    #             query_start = time.time()
    #             cursor.execute(chapter_query)
    #         except:
    #             raise UserError("Database is not responding please try after sometime.")
    #         query_response = cursor.fetchall()
    #         cursor.close()
    #         now = time.time()
    #
    #         db_logs_create = self.env['db.logs'].create(
    #             {'dl_id': self.reference, 'dl_code': dl_code, 'dl_time': (now - query_start)})
    #
    #         if len(query_response) == 0:
    #             raise UserError('Sorry, there are no questions available for the selected subject at the moment. '
    #                             'Kindly choose another subject.')
    #         details_list = []
    #         for rec in query_response:
    #             details_list.append((0, 0,
    #                                  {"ql_criteria": int(self.selection_criteria), "ql_criteria_name": 'Chapter',
    #                                   "ql_idx_id": rec[0],
    #                                   "ql_name": rec[1], "ql_q_count": rec[2]}))
    #
    #         self.env['education.exam'].browse(self._origin.id).write({'question_list': details_list})
    #
    #     elif self.selection_criteria == '2':
    #         if standard <= 8:
    #             q_type = (1, 2)
    #             dl_code = 'S25'
    #         elif standard > 8:
    #             q_type = (1, 100)
    #             dl_code = 'S29'
    #
    #         topic_query = """select ed.topic_unique_id,topic_name,count(distinct(ed.q_id)),ed.chapter_unique_id,chapter_name from tnschools_working.exams_quest_detail ed inner join
    #                         tnschools_working.exams_quest_bank eb on ed.q_id=eb.q_id inner join
    #                         tnschools_working.schoolnew_taxonomy st on st.taxonomy_id=ed.taxonomy_id
    #                         where q_type in {} and q_format in (2,3,4) and eb.created_date>'2022-10-10' and status=4 and assessment_status=1  and
    #                         st.chapter_unique_id={} group by ed.topic_unique_id;""".format(str(q_type),
    #                                                                                        int(self.chapter_dropdown.cl_chapter_idx))
    #         try:
    #             query_start = time.time()
    #             cursor.execute(topic_query)
    #         except:
    #             raise UserError("Database is not responding please try after sometime.")
    #         query_response = cursor.fetchall()
    #         cursor.close()
    #         now = time.time()
    #         db_logs_create = self.env['db.logs'].create(
    #             {'dl_id': self.reference, 'dl_code': dl_code, 'dl_time': (now - query_start)})
    #         if len(query_response) == 0:
    #             raise UserError('Sorry, there are no questions available for the selected subject at the moment. '
    #                             'Kindly choose another subject.')
    #         details_list = []
    #         for rec in query_response:
    #             details_list.append((0, 0,
    #                                  {"ql_criteria": int(self.selection_criteria), "ql_criteria_name": 'Topic',
    #                                   "ql_idx_id": rec[0],
    #                                   "ql_name": rec[1], "ql_q_count": rec[2],
    #                                   "ql_chapter_idx_id": rec[3], "ql_chapter": rec[4]}))
    #
    #         self.env['education.exam'].browse(self._origin.id).write({'question_list': details_list})
    #
    #     elif self.selection_criteria == '3':
    #         if standard <= 8:
    #             q_type = (1, 2)
    #             dl_code = 'S35'
    #         elif standard > 8:
    #             q_type = (1, 100)
    #             dl_code = 'S39'
    #
    #         sub_topic_query = """select ed.subtopic_unique_id,sub_topic_name,count(distinct(ed.q_id)),ed.chapter_unique_id,chapter_name, ed.topic_unique_id from tnschools_working.exams_quest_detail ed inner join
    #                             tnschools_working.exams_quest_bank eb on ed.q_id=eb.q_id inner join
    #                             tnschools_working.schoolnew_taxonomy st on st.taxonomy_id=ed.taxonomy_id
    #                             where q_type in {} and q_format in (2,3,4) and eb.created_date>'2022-10-10' and status=4 and assessment_status=1 and
    #                             st.chapter_unique_id={} and st.topic_unique_id={}  and ed.subtopic_unique_id is not null group by ed.subtopic_unique_id;""".format(
    #             str(q_type), int(self.chapter_dropdown.cl_chapter_idx), int(self.topic_dropdown.tl_topic_idx))
    #         try:
    #             query_start = time.time()
    #             cursor.execute(sub_topic_query)
    #         except:
    #             raise UserError("Database is not responding please try after sometime.")
    #         query_response = cursor.fetchall()
    #         cursor.close()
    #         now = time.time()
    #         db_logs_create = self.env['db.logs'].create(
    #             {'dl_id': self.reference, 'dl_code': dl_code, 'dl_time': (now - query_start)})
    #         if len(query_response) == 0:
    #             raise UserError('Sorry, there are no questions available for the selected subject at the moment. '
    #                             'Kindly choose another subject.')
    #         details_list = []
    #         for rec in query_response:
    #             details_list.append(
    #                 (0, 0,
    #                  {"ql_criteria": int(self.selection_criteria), "ql_criteria_name": 'Subtopic', "ql_idx_id": rec[0],
    #                   "ql_name": rec[1],
    #                   "ql_q_count": rec[2],
    #                   "ql_chapter_idx_id": rec[3],
    #                   "ql_topic_idx_id": rec[5], "ql_chapter": rec[4]}))
    #
    #         self.env['education.exam'].browse(self._origin.id).write({'question_list': details_list})
    #
    #     return

    def search_jn(self):
        for rec in self.question_list:
            rec.unlink()
        # print("exam type jn", self.exam_type)
        medium = int(self.medium)
        standard = int(self.standard_dropdown)
        subject = int(self.subject.subject_code)
        if standard == 12:
            standard = (11, 12)
        conn = mysql.connector.connect(host='',
                                       password='', user='', port=3306, database='tnschools_working')
        cursor = conn.cursor()
        if self.selection_criteria == '1':
            dl_code = 'SJN'
            # print(q_type, term)

            chapter_query = """select ed.chapter_unique_id,chapter_name,count(distinct(ed.q_id)),class_studying_id from tnschools_working.exams_quest_detail ed inner join
                                tnschools_working.exams_quest_bank eb on ed.q_id=eb.q_id inner join
                                tnschools_working.schoolnew_taxonomy st on st.taxonomy_id=ed.taxonomy_id
                                where  q_difficulty in (1,2,3) and q_category in (7,8)  
                                and medium_id={} and class_studying_id {} and subject_id={} and ed.chapter_unique_id is not null
                                 group by ed.chapter_unique_id
                                 order by class_studying_id desc;""".format(
                medium, f"in {standard}" if isinstance(standard, tuple) else f"= {standard}", subject)
            try:
                query_start = time.time()
                cursor.execute(chapter_query)
            except:
                raise UserError("Database is not responding please try after sometime.")
            query_response = cursor.fetchall()
            cursor.close()
            now = time.time()
            # print(now - query_start)
            db_logs_create = self.env['db.logs'].create(
                {'dl_id': self.reference, 'dl_code': dl_code, 'dl_time': (now - query_start)})
            # print(len(query_response))
            if len(query_response) == 0:
                raise UserError('Sorry, there are no questions available for the selected subject at the moment. '
                                'Kindly choose another subject.')
            details_list = []
            for rec in query_response:
                details_list.append((0, 0,
                                     {"ql_criteria": int(self.selection_criteria), "ql_criteria_name": 'Chapter',
                                      "ql_idx_id": rec[0],
                                      "ql_name": rec[1], "ql_q_count": rec[2], "ql_standard": rec[3]}))

            self.env['education.exam'].browse(self._origin.id).write({'question_list': details_list})
        return

    # # ##########################################JEE NEET ##################create jn########################################

    def create_jn(self):
        # program_start=time.time()
        checkbox_count = 0
        for line in self.question_list:
            if line.checkbox:
                checkbox_count = checkbox_count + 1
        if checkbox_count == 0:
            if self.selection_criteria == '1':
                raise UserError('Select atleast one chapter!')
            # elif self.selection_criteria == '2':
            #     raise UserError('Select atleast one topic!')
            # elif self.selection_criteria == '3':
            #     raise UserError('Select atleast one subtopic!')
        q_id_l = []
        for rec in self.question_set:
            q_id_l.append(int(rec.q_id))
        # print(q_id_l)
        questions_insert = 0
        conn = mysql.connector.connect(host='',
                                       password='', user='', port=3306, database='tnschools_working')
        cursor = conn.cursor()
        chapter_list = []
        difficulty_val = [1, 2, 3]

        for line in self.question_list:
            if line.checkbox:
                for d in difficulty_val:
                    # print("difficulty",d)
                    criteria = line.ql_criteria
                    set_counter = 1
                    for line_count in self.question_set_count_view:
                        set_counter = set_counter + 1

                    standard = int(self.standard_dropdown)
                    dl_code = 'QJN'
                    if criteria == 1:
                        # print(d)
                        # print(line.ql_idx_id)
                        cursor = conn.cursor()
                        q_query = """select ed.q_id,eb.q_text,ed.q_difficulty,ed.chapter_unique_id from tnschools_working.exams_quest_detail ed inner join
                                    tnschools_working.exams_quest_bank eb on ed.q_id=eb.q_id
                                    where  q_category in (7,8) and ed.q_difficulty={} and ed.chapter_unique_id={};""".format(
                            d, line.ql_idx_id)

                    try:
                        # print(q_query)
                        query_start = time.time()
                        cursor.execute(q_query)
                    except Exception as error:
                        # print(error)
                        raise UserError("Database is not responding please try after sometime.")
                    q_query_response = cursor.fetchall()
                    # To handle the case when any difficulty have 0 questions
                    if (len(q_query_response) == 0):
                        break
                    cursor.close()
                    now = time.time()
                    db_logs_create = self.env['db.logs'].create(
                        {'dl_id': self.reference, 'dl_code': dl_code, 'dl_time': (now - query_start)})
                    count = 0
                    question_list = []

                    for rec in q_query_response:
                        soup = BeautifulSoup(str(rec[1]), "html.parser")
                        string_question = soup.get_text()
                        if rec[0] in q_id_l:
                            count = count + 1
                        else:
                            question_list.append((0, 0, {"q_text": string_question,
                                                         "q_id": rec[0], "set_no": set_counter,
                                                         "subject_id": self.subject.id}))

                    if count == len(q_query_response):
                        if criteria == 1:
                            raise UserError('Sorry all questions from selected chapter/chapters are already present .')
                        # if criteria == 2:
                        #     raise UserError('Sorry all questions from selected topic/topics are already present .')
                        # if criteria == 3:
                        #     raise UserError(
                        #         'Sorry all questions from selected subtopic/subtopics are already present .')
                    self.env['education.exam'].browse(self.id).write({'question_set': question_list})

                    summary_view = (0, 0,
                                    {"set_number": set_counter, "set_count": len(question_list),
                                     "set_description": line.ql_name,
                                     "questions_insert": questions_insert, "qc_subject_id": self.subject.id,
                                     "set_subject": self.subject.subject_code, "qc_difficulty": rec[2],
                                     "qc_chapter_id": rec[3], "qc_standard": line.ql_standard})

                    self.env['education.exam'].browse(self.id).write({'question_set_count_view': [summary_view]})
        self.deselect_all()
        return

    def create_group_mcq(self):
        checkbox_count = 0
        for line in self.question_list:
            if line.checkbox:
                checkbox_count = checkbox_count + 1
        if checkbox_count == 0:
            if self.selection_criteria == '1':
                raise UserError('Select atleast one chpater!')
            elif self.selection_criteria == '2':
                raise UserError('Select atleast one topic!')

            # elif self.selection_criteria == '3':
            #     raise UserError('Select atleast one subtopic!')
        q_id_l = []
        for rec in self.question_set:
            q_id_l.append(int(rec.q_id))

        if self.exam_type == '2' and int(self.standard_dropdown) < 11:
            questions_insert = 6
        else:
            questions_insert = 5
        question_list = []
        # conn = mysql.connector.connect(host='',
        #                                password='', user='', port=3306, database='tnschools_working')
        # cursor = conn.cursor()
        chapter_list = []
        topic_list = []
        subtopic_list = []
        for line in self.question_list:
            set_counter = 1
            for line_count in self.question_set_count_view:
                set_counter = set_counter + 1
            con_subject = self.subject.smt_subject_name
            con_standard = self.standard_dropdown
            description = str(con_subject) + '_' + str(con_standard)
            if line.checkbox:
                if line.ql_criteria == 1:
                    chapter_list.append(line.ql_idx_id)
                elif line.ql_criteria == 2:
                    topic_list.append(line.ql_idx_id)
                    chapter_list.append(
                        line.ql_chapter_idx_id) if line.ql_chapter_idx_id not in chapter_list else chapter_list
                # elif line.ql_criteria == 3:
                #     subtopic_list.append(line.ql_idx_id)
                #     topic_list.append(line.ql_topic_idx_id) if line.ql_topic_idx_id not in topic_list else topic_list
                #     chapter_list.append(
                #         line.ql_chapter_idx_id) if line.ql_chapter_idx_id not in chapter_list else chapter_list
                criteria = line.ql_criteria


        standard = int(self.standard_dropdown)
        if standard <= 8:
            q_type = (1, 2)
            dl_code = 'Q{}5'
        elif standard > 8:
            q_type = (1, 100)
            dl_code = 'Q{}9'
        if len(chapter_list) == 1:
            chapter_list.append(0)
        if len(topic_list) == 1:
            topic_list.append(0)
        if len(subtopic_list) == 1:
            subtopic_list.append(0)
        chapter_tuple = tuple(chapter_list)
        topic_tuple = tuple(topic_list)
        subtopic_tuple = tuple(subtopic_list)

        if criteria == 1:
            q_query = """select qmt_question_code,qmt_q_text from question_master_table
            where qmt_taxonomy_code in (select stm_taxonomy_code
            from subject_taxonomy_master
            where stm_chapter_code in %s
            )"""
            self.env.cr.execute(q_query, (chapter_tuple,))
        elif criteria == 2:
            q_query = """select qmt_question_code,qmt_q_text 
            from question_master_table
            where qmt_taxonomy_code in (select stm_taxonomy_code
            from subject_taxonomy_master
            where stm_chapter_code in %s and stm_topic_code in %s)"""
            self.env.cr.execute(q_query, (chapter_tuple,topic_tuple))

        # elif criteria == 3:
        #     q_query = """select ed.q_id,eb.q_text from tnschools_working.exams_quest_detail ed inner join
        #                 tnschools_working.exams_quest_bank eb on ed.q_id=eb.q_id
        #                 where q_type in {} and q_format in (2,3,4) and eb.created_date>'2022-10-10' and status=4 and assessment_status=1
        #                 and ed.chapter_unique_id in {} and ed.topic_unique_id in {} and ed.subtopic_unique_id in {};""".format(
        #         q_type, chapter_tuple, topic_tuple, subtopic_tuple)
        #     dl_code = dl_code.format(criteria)
        try:
            # self.env.cr.execute(q_query, (chapter_tuple,))
            q_query_response = self.env.cr.fetchall()
            # print('q_query_response', q_query_response)
        except:
            raise UserError("Database is not responding please try after sometime.")
        # q_query_response = cursor.fetchall()
        # now = time.time()
        # db_logs_create = self.env['db.logs'].create(
        #     {'dl_id': self.reference, 'dl_code': dl_code, 'dl_time': (now - query_start)})
        count = 0
        for rec in q_query_response:
            soup = BeautifulSoup(str(rec[1]), "html.parser")
            string_question = soup.get_text()
            if rec[0] in q_id_l:
                # print('q_id_l', q_id_l)
                count = count + 1
            else:
                question_list.append((0, 0, {"q_text": string_question,
                                             "q_id": rec[0], "set_no": set_counter,
                                             "subject_id": self.subject.id,
                                             }))
        if count == len(q_query_response):
            if criteria == 1:
                raise UserError('Sorry all questions from selected chapter/chapters are already present .')
            if criteria == 2:
                raise UserError('Sorry all questions from selected topic/topics are already present .')
            if criteria == 3:
                raise UserError('Sorry all questions from selected subtopic/subtopics are already present .')
        self.env['education.exam'].browse(self.id).write({'question_set': question_list})
        summary_view = (0, 0,
                        {"set_number": set_counter, "set_count": len(question_list), "set_description": description,
                         "questions_insert": questions_insert, "set_subject": self.subject.smt_subject_code,
                         "qc_subject_id": self.subject.id
                         },
                        )
        # print('summary_view',summary_view)

        self.env['education.exam'].browse(self.id).write({'question_set_count_view': [summary_view]})
        self.deselect_all()
        return


class SubjectLine(models.Model):
    _name = 'education.subject.line'
    _description = 'Subject Line'

    subject_id = fields.Many2one('education.subject', string='Subject', required=True)
    date = fields.Date(string='Date', required=True)
    time_from = fields.Float(string='Time From', required=True)
    time_to = fields.Float(string='Time To', required=True)
    mark = fields.Integer(string='Mark')
    exam_id = fields.Many2one('education.exam', string='Exam')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get())


class EducationExamType(models.Model):
    _name = 'education.exam.type'
    _description = 'Education Exam Type'

    name = fields.Char(string='Name', required=True)
    school_class_division_wise = fields.Selection([('school', 'School'), ('class', 'Class'), ('division', 'Division'), (
        'final', 'Final Exam (Exam that promotes students to the next class)')], string='Exam Type', default='class')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get())


# Change Table name
class QuestionPaper(models.Model):
    _name = 'question.paper'
    _description = 'Question Paper'
    _rec_name = 'q_text'
    checkbox = fields.Boolean(string="Checkbox", default=False)
    q_id = fields.Char('Question ID', required=False)
    q_text = fields.Char(string='Question', required=True)
    subject_id = fields.Many2one('question.subject', string='Subject', required=True)
    mark_id = fields.Many2one('question.mark', string='Marks')
    medium_id = fields.Selection([('tamil', 'Tamil'), ('english', 'English')], string='Medium')
    standard_id = fields.Many2one('question.standard', string='Standard', required=True)
    isactive = fields.Boolean(string="Is Active")
    exam_id = fields.Many2one('education.exam', string='Exam')


# Change Table name
class SelectedQuestionPaper(models.Model):
    _name = 'selected.question.paper'
    _description = 'Selected Question Paper'
    _rec_name = 'q_text'
    checkbox = fields.Boolean(string="Checkbox")
    q_text = fields.Char(string='Question', required=True)
    q_id = fields.Char('Question ID', required=False)
    subject_id = fields.Many2one('question.subject', string='Subject')
    mark_id = fields.Many2one('question.mark', string='Marks')
    medium_id = fields.Selection([('tamil', 'Tamil'), ('english', 'English')], string='Medium')
    standard_id = fields.Many2one('question.standard', string='Standard')
    isactive = fields.Boolean(string="Is Active")
    sel_exam_id = fields.Many2one('education.exam', string='Exam')


# Change Table name
class PaperSet(models.Model):
    _name = 'selected.question.set'
    _description = 'Question Paper Set'
    _rec_name = 'q_text'
    checkbox = fields.Boolean(string="Checkbox", default=False)
    q_text = fields.Char(string='Question', required=True)
    q_id = fields.Char('Question ID', required=False)
    subject_id = fields.Many2one('subject.master.table', string='Subject')
    mark_id = fields.Many2one('question.mark', string='Marks')
    medium_id = fields.Selection([('tamil', 'Tamil'), ('english', 'English')], string='Medium')
    standard_id = fields.Many2one('question.standard', string='Standard')
    isactive = fields.Boolean(string="Is Active")
    # q_difficulty = fields.Selection([('bas', 'Basic'), ('int', 'Intermediate'), ('adv', 'Advanced')],
    #                                 string='Difficulty')
    set_id = fields.Many2one('education.exam', string='Set ID')
    set_no = fields.Integer(string='Group No.', required=True)
    # JeeNeet
    ql_difficulty = fields.Integer('Difficulty Level')
    ql_difficulty_text = fields.Char(string='Difficulty', compute='_compute_ql_difficulty')

    @api.depends('ql_difficulty')
    def _compute_ql_difficulty(self):
        for q in self:
            if q.ql_difficulty == 1:
                q.ql_difficulty_text = 'Easy'
            elif q.ql_difficulty == 2:
                q.ql_difficulty_text = 'Medium'
            else:
                q.ql_difficulty_text = 'Hard'


# Change Table name
class PaperSetCount(models.Model):
    _name = 'question.set.count'
    _description = 'Set count'
    _rec_name = 'set_number'
    checkbox = fields.Boolean(string="Checkbox", default=False)
    set_number = fields.Integer('Group Number')
    set_count = fields.Integer('Available questions')
    set_count_id = fields.Many2one('education.exam', string='Set ID')
    questions_insert = fields.Integer(string='Questions to insert')
    set_description = fields.Char(string='Group Description')
    setsection = fields.Many2one('set.section', string='Group Section (Optional)')
    set_subject = fields.Integer('Subject')
    # JeeNeet
    qc_subject_id = fields.Many2one('subject.master.table', string='Subject')
    qc_criteria_name = fields.Char('Criteria')
    qc_name = fields.Char('Name')  ###Chapter/topic/subtopic name
    qc_chapter_id = fields.Integer('Chapter ID')
    qc_difficulty = fields.Integer('Difficulty Level')

    qc_difficulty_text = fields.Char(string='Difficulty', compute='_compute_qc_difficulty')
    qc_standard = fields.Char('Standard')

    @api.depends('qc_difficulty')
    def _compute_qc_difficulty(self):
        for q in self:
            if q.qc_difficulty == 1:
                q.qc_difficulty_text = 'Easy'
            elif q.qc_difficulty == 2:
                q.qc_difficulty_text = 'Medium'
            else:
                q.qc_difficulty_text = 'Hard'


class DesignPaper(models.Model):
    _name = 'question.paper.design'
    _description = 'Paper Design'
    _rec_name = 'q_text'
    q_id = fields.Char('Question ID', required=False)
    q_text = fields.Char(string='Question', required=True)
    subject_id = fields.Many2one('question.subject', string='Subject')
    standard_id = fields.Many2one('question.standard', string='Standard')
    isactive = fields.Boolean(string="Is Active")
    design_id = fields.Many2one('education.exam', string='Design ID')
    set_no = fields.Integer(string='Set No.')
    setsection_id = fields.Char(string='Set Section')


class VersionMaster(models.Model):
    _name = 'version.master'
    _description = 'Create Version'
    _rec_name = ''
    cvm_design_version_id = fields.Char(string=' Design Version ID', required=True, copy=False, readonly=True,
                                        default=lambda self: _('New'))
    cvm_design_id = fields.Many2one('education.exam', string='Design ID*')
    cvm_version_count = fields.Integer(string='No. of versions(max 5)*')
    cvm_paper_no = fields.Integer(string='No. of sets(max 10)*')
    cvm_set_no = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'),
         ('9', '9'), ('10', '10')], string='No. of sets(max 10)*', default='5')
    cvm_version_no = fields.Selection([('1', '1'), ('2', '2'), ('3', '3'), ('3', '3'), ('4', '4'), ('5', '5')],
                                      string='No. of versions(max 5)*', default='5')
    # cvm_set_count=fields.Selection()
    cvm_question_random_option = fields.Char(string='Question Shuffle')
    cvm_summary_view = fields.One2many('version.set.summary', 'cvs_design_version_id', string='Set Summary')
    cvm_shuffle_op = fields.Selection([('1', 'Yes'), ('2', 'No')], string='Set section shuffling')
    # cvm_event_id = fields.Integer(string='Event ID')
    cvm_paper_version = fields.One2many('version.paper.question', 'cvp_design_version_id', string='Paper')
    cvm_paper_version_id = fields.Char("Version ID")
    cvm_paper_allocation = fields.One2many('paper.allocation', 'pa_design_version_id', string='Paper Allocation')
    cvm_state = fields.Selection(
        [('vs', 'Version start'), ('vc', 'Version Completion'), ('als', 'Allocation start'), ('alc', 'Allocated'),
         ('cnf', 'Confirm')], string='State', default='vs')
    cvm_schedule_details = fields.One2many('schedule.details', 'design_version_id', string='Schedule Details')
    cvm_event_details = fields.Many2one('schedule.details', string='Schedule Details*')
    cvm_event_details_domain = fields.Char(compute="_compute_event_domain", readonly=True, store=False)
    cvm_total_questions = fields.Integer('Total Questions', compute="_compute_total")
    cvm_total_time = fields.Integer('Total Time(mins)*', default=60)
    cvm_is_1_n = fields.Integer('Event Type')
    # cvm_allocation_status=fields.Integer('Allocation Status')
    ###########################################################JEENEET#################
    cvm_hard_percent = fields.Integer('Hard     %', compute="_compute_hard")
    cvm_medium_percent = fields.Integer('Medium   %')
    cvm_easy_percent = fields.Integer('Easy     %')
    cvm_total_questions_jn = fields.Integer('Total Questions per Subject', onchange="_compute_hard_medium_easy")
    cvm_subjects = fields.Char('Selected Subject')
    cvm_max_questions = fields.Integer('Maximum questions limit ', compute="_compute_max")
    cvm_exam_type = fields.Integer('Exam Type')

    @api.model
    def create(self, vals):
        if vals.get('cvm_design_version_id', _('New')) == _('New'):
            vals['cvm_design_version_id'] = self.env['ir.sequence'].next_by_code('design.version.number') or _('New')
        res = super(VersionMaster, self).create(vals)
        self.cvm_state = 'vs'
        return res

    @api.depends('cvm_design_id')
    def _compute_event_domain(self):
        for rec in self:
            rec.cvm_event_details_domain = json.dumps([('schedule_id', '=', self.cvm_design_id.cdac_schedule_id)])

    ####################################################################JEENEET####################################################
    @api.onchange('cvm_total_questions_jn')
    def _compute_hard_medium_easy(self):
        if self.cvm_total_questions_jn > self.cvm_max_questions:
            raise UserError('Sufficient questions not available ')
        if self.cvm_total_questions_jn:
            subject_ids = set(rec.cvs_subject_id for rec in self.cvm_summary_view)
            hard_list = []
            medium_list = []

            for subject_id in subject_ids:
                hard_sum = 0
                medium_sum = 0

                for line in self.cvm_summary_view:
                    if line.cvs_subject_id == subject_id:
                        if line.cvs_difficulty == 3:
                            hard_sum += line.cvs_av_qs
                        elif line.cvs_difficulty == 2:
                            medium_sum += line.cvs_av_qs

                hard_list.append(hard_sum)
                medium_list.append(medium_sum)

            min_hard = min(hard_list)
            min_medium = min(medium_list)
            required_hard_percent = 100
            temp_hard_percent = round((min_hard / self.cvm_total_questions_jn) * 100)
            if temp_hard_percent >= required_hard_percent:
                temp_hard_percent = 100
                temp_medium_percent = 0
                temp_easy_percent = 0
            else:
                required_medium_percent = 100 - temp_hard_percent
                temp_medium_percent = round((min_medium / self.cvm_total_questions_jn) * 100)
                if temp_medium_percent > required_medium_percent:
                    temp_medium_percent = required_medium_percent
                temp_easy_percent = 100 - (temp_hard_percent + temp_medium_percent)

            self.cvm_hard_percent = temp_hard_percent
            self.cvm_medium_percent = temp_medium_percent
            self.cvm_easy_percent = temp_easy_percent

    @api.depends('cvm_easy_percent', 'cvm_medium_percent')
    def _compute_hard(self):
        for rec in self:
            rec.cvm_hard_percent = 100 - (rec.cvm_easy_percent + rec.cvm_medium_percent)

    def _compute_total(self):
        total = 0
        # print('Function call')
        for rec in self.cvm_summary_view:
            total = rec.cvs_in_qs + total
        self.cvm_total_questions = total

    def _compute_max(self):
        subject_ids = set(rec.cvs_subject_id for rec in self.cvm_summary_view)
        sum_list = []
        for subject_id in subject_ids:
            sum_av = 0
            for line in self.cvm_summary_view:
                if line.cvs_subject_id == subject_id:
                    sum_av += line.cvs_av_qs
                    # print(sum_av)

            sum_list.append(sum_av)
        # print(sum_list)
        self.cvm_max_questions = min(sum_list)
        # print("max questions",self.cvm_max_questions)

    @api.onchange('cvm_easy_percent', 'cvm_medium_percent')
    def _onchange_percent_fields(self):
        if self.cvm_easy_percent < 0:
            self.cvm_easy_percent = 0
        elif self.cvm_easy_percent > 100:
            self.cvm_easy_percent = 100

        if self.cvm_medium_percent < 0:
            self.cvm_medium_percent = 0
        elif self.cvm_medium_percent > 100:
            self.cvm_medium_percent = 100

        remaining_percent = 100 - self.cvm_easy_percent - self.cvm_medium_percent
        if remaining_percent < 0:
            self.cvm_easy_percent = max(0, self.cvm_easy_percent + remaining_percent)
            self.cvm_medium_percent = max(0, self.cvm_medium_percent + remaining_percent)
            self.cvm_hard_percent = 100 - (self.cvm_easy_percent + self.cvm_medium_percent)

    def calculate_jn(self):
        # program_start = time.time()
        print('Calculate JN')
        subject_ids = set(rec.cvs_subject_id for rec in self.cvm_summary_view)
        no_of_subjects = len(subject_ids)

        total_questions_per_subject = self.cvm_total_questions_jn
        if self.cvm_easy_percent < 0 or self.cvm_medium_percent < 0 or self.cvm_hard_percent < 0:
            raise UserError('Please modify the incorrect percentage values!')

        subject_id_to_name = {}
        for rec in self.cvm_summary_view:
            subject_id = rec.cvs_subject_id
            subject_name = rec.cvs_subject_name
            subject_id_to_name[subject_id] = subject_name

        for subject_id, subject_name in subject_id_to_name.items():
            easy_qc = round(total_questions_per_subject * self.cvm_easy_percent / 100)
            medium_qc = round(total_questions_per_subject * self.cvm_medium_percent / 100)
            hard_qc = total_questions_per_subject - (easy_qc + medium_qc)
            easy_qc_before = easy_qc
            medium_qc_before = medium_qc
            hard_qc_before = hard_qc
        # print("\nSubject Id (Before Adjustment1)", subject_id, "\nEasy", easy_qc, "Medium", medium_qc, "Hard", hard_qc)

        for subject_id, subject_name in subject_id_to_name.items():
            subject_rec = subject_id
            subject_name_for_error = subject_name
            easy_av_sum = 0
            medium_av_sum = 0
            hard_av_sum = 0
            easy_qc = easy_qc_before
            medium_qc = medium_qc_before
            hard_qc = hard_qc_before

            for recc in self.cvm_summary_view:
                if recc.cvs_subject_id == subject_rec:
                    if recc.cvs_difficulty == 1:
                        easy_av_sum += recc.cvs_av_qs
                    elif recc.cvs_difficulty == 2:
                        medium_av_sum += recc.cvs_av_qs
                    elif recc.cvs_difficulty == 3:
                        hard_av_sum += recc.cvs_av_qs
            # print("\nSubject id", subject_rec, "\nEasy sum", easy_av_sum, "Medium sum", medium_av_sum, "Hard sum",hard_av_sum)
            total_available_questions_in_subject = easy_av_sum + medium_av_sum + hard_av_sum
            if easy_av_sum < easy_qc:
                easy_qc, medium_qc, hard_qc = self.question_count_adjustment(easy_qc, easy_av_sum, medium_av_sum,
                                                                             medium_qc, hard_av_sum, hard_qc,
                                                                             subject_name_for_error,
                                                                             total_available_questions_in_subject)

            if medium_av_sum < medium_qc:
                medium_qc, hard_qc, easy_qc = self.question_count_adjustment(medium_qc, medium_av_sum, hard_av_sum,
                                                                             hard_qc, easy_av_sum, easy_qc,
                                                                             subject_name_for_error,
                                                                             total_available_questions_in_subject)

            if hard_av_sum < hard_qc:
                hard_qc, medium_qc, easy_qc = self.question_count_adjustment(hard_qc, hard_av_sum,
                                                                             medium_av_sum,
                                                                             medium_qc, easy_av_sum, easy_qc,
                                                                             subject_name_for_error,
                                                                             total_available_questions_in_subject)

            # print("Subject Id(after adjustment)", subject_id, "\nEasy", easy_qc, "Medium", medium_qc, "Hard", hard_qc)

            remaining_easy_qc = easy_qc
            remaining_medium_qc = medium_qc
            remaining_hard_qc = hard_qc
            #             To mark when remaining lines have to be assigned 0 value, the case where remaining
            # easy,medium or hard qc is consumed completely.

            flag_easy_zero = 0
            flag_medium_zero = 0
            flag_hard_zero = 0

            sum_easy = 0
            sum_medium = 0
            sum_hard = 0
            group_no_hard = []
            group_no_medium = []
            group_no_easy = []
            for line in self.cvm_summary_view:
                if line.cvs_subject_id == subject_rec:
                    if line.cvs_difficulty == 3:
                        group_no_hard, flag_hard_zero, remaining_hard_qc, sum_hard, line.cvs_in_qs = self.calculate_questions_to_insert(
                            group_no_hard, line.cvs_set_no, flag_hard_zero, line.cvs_av_qs, hard_av_sum, hard_qc,
                            remaining_hard_qc, sum_hard)

                    elif line.cvs_difficulty == 2:
                        group_no_medium, flag_medium_zero, remaining_medium_qc, sum_medium, line.cvs_in_qs = self.calculate_questions_to_insert(
                            group_no_medium, line.cvs_set_no, flag_medium_zero, line.cvs_av_qs, medium_av_sum,
                            medium_qc, remaining_medium_qc, sum_medium)

                    elif line.cvs_difficulty == 1:
                        group_no_easy, flag_easy_zero, remaining_easy_qc, sum_easy, line.cvs_in_qs = self.calculate_questions_to_insert(
                            group_no_easy, line.cvs_set_no, flag_easy_zero, line.cvs_av_qs, easy_av_sum,
                            easy_qc, remaining_easy_qc, sum_easy)

            easy_gap = easy_qc - sum_easy
            medium_gap = medium_qc - sum_medium
            hard_gap = hard_qc - sum_hard

            self.process_gaps(easy_gap, group_no_easy)
            self.process_gaps(medium_gap, group_no_medium)
            self.process_gaps(hard_gap, group_no_hard)

        total_questions_to_insert = 0
        for r in self.cvm_summary_view:
            total_questions_to_insert = r.cvs_in_qs + total_questions_to_insert
        self.cvm_total_questions = total_questions_to_insert
        for rec in self.cvm_summary_view:
            if rec.cvs_in_qs == 0:
                rec.unlink()
        return

    def process_gaps(self, gap, group_numbers):
        if gap != 0:
            for group_no in reversed(group_numbers):
                for l in self.cvm_summary_view:
                    if l.cvs_set_no == group_no and l.cvs_av_qs - l.cvs_in_qs > gap:
                        l.cvs_in_qs += gap
                        # print("group no", group_no)
                        gap = 0
                        break
        return

    def question_count_adjustment(self, diff_qc, diff_av_sum, level1_av_sum, level1_qc, level2_av_sum, level2_qc,
                                  subject_name_for_error, total_available_questions_in_subject):
        # calculate shortage
        difficulty_shortage = diff_qc - diff_av_sum
        diff_qc -= difficulty_shortage
        if level1_av_sum - level1_qc >= 1 and difficulty_shortage != 0:
            if level1_av_sum - level1_qc >= difficulty_shortage:
                level1_qc += difficulty_shortage
                difficulty_shortage = 0
            else:
                available_level1 = level1_av_sum - level1_qc
                level1_qc += available_level1
                difficulty_shortage -= available_level1
        if level2_av_sum - level2_qc >= 1 and difficulty_shortage != 0:
            if level2_av_sum - level2_qc >= difficulty_shortage:
                level2_qc += difficulty_shortage
                difficulty_shortage = 0
            else:
                available_level2 = level2_av_sum - level2_qc
                level2_qc += available_level2
                difficulty_shortage -= available_level2
        if difficulty_shortage != 0:
            raise UserError(
                'Sufficient questions not available in ' + subject_name_for_error + '. Maximum available is ' + str(
                    total_available_questions_in_subject))
        return diff_qc, level1_qc, level2_qc

    def calculate_questions_to_insert(self, group_no_difficulty, group_no, flag_diff_zero, cvs_av_qs, diff_av_sum,
                                      diff_qc, remaining_diff_qc, sum_diff):
        group_no_difficulty.append(group_no)
        if flag_diff_zero == 1:
            round_temp_cvs_in_qs = 0
            cvs_in_qs_final = round_temp_cvs_in_qs
        else:
            temp_fraction = cvs_av_qs / diff_av_sum
            temp_cvs_in_qs = diff_qc * temp_fraction
            if temp_cvs_in_qs < 1 and temp_cvs_in_qs != 0:
                round_temp_cvs_in_qs = 1
            elif temp_cvs_in_qs == 0:
                round_temp_cvs_in_qs = 0
            else:
                round_temp_cvs_in_qs = round(temp_cvs_in_qs)
                if round_temp_cvs_in_qs > remaining_diff_qc:
                    round_temp_cvs_in_qs = remaining_diff_qc
            remaining_diff_qc -= round_temp_cvs_in_qs
            cvs_in_qs_final = round_temp_cvs_in_qs
            if remaining_diff_qc == 0:
                flag_diff_zero = 1
        sum_diff += cvs_in_qs_final
        return group_no_difficulty, flag_diff_zero, remaining_diff_qc, sum_diff, cvs_in_qs_final

    def generate_paper(self):
        # if self.cvm_exam_type in [3, 4]:
        #     self.calculate_jn()
        if self.cvm_paper_version:
            flag1 = 1
        else:
            flag1 = 0
            for line in self:
                line.cvm_paper_version.unlink()
            if self.cvm_state == 'vc' or self.cvm_state == 'als' or self.cvm_state == 'alc' or self.cvm_state == 'cnf':
                raise UserError('Paper already generated.')
            self.cvm_state = 'vc'
            if (int(self.cvm_set_no)) < 1 or (int(self.cvm_version_no)) < 1:
                raise UserError("Please enter value greater than 0 for No. sets and No. of versions")
            # if self.cvm_is_1_n == 1:
            #     participant_pk = self.cvm_design_id.participant_pk
                # print('1:N event')
            question_corpus = {}
            result = self.env['version.set.summary'].search(
                [('cvs_design_version_id', '=', self.id)])
            c = 0.2
            reserved = {}
            unreserved = {}
            set = []
            subject_list = []
            subject_d = {}
            for rec in result:
                set.append(rec.cvs_set_no)
                if rec.cvs_subject_id in subject_list:
                    temp_list = subject_d.get(rec.cvs_subject_id)
                    temp_list.append(rec.cvs_set_no)
                else:
                    subject_list.append(rec.cvs_subject_id)
                    temp_list = []
                    temp_list.append(rec.cvs_set_no)
                    subject_d.update({rec.cvs_subject_id: temp_list})
                question = self.env['selected.question.set'].search(
                    ['&', ('set_id', '=', self.cvm_design_id.id), ('set_no', '=', rec.cvs_set_no)])
                question_list = []
                for q in question:
                    question_list.append(q.q_id)
                question_corpus.update({rec.cvs_set_no: {'qid': question_list, 'count': rec.cvs_in_qs}})
                icount = rec.cvs_in_qs
                reserved_count = round(c * icount)
                reserved_list = random.sample(question_list, reserved_count)
                unreserved_list = [i for i in question_list if i not in reserved_list]
                unreserved_count = icount - reserved_count
                unreserved.update({rec.cvs_set_no: {'qid': unreserved_list, 'count': unreserved_count}})
                reserved.update({rec.cvs_set_no: {'qid': reserved_list}})
            d_unreserved = unreserved.copy()

            paper_version = []
            for paper in range(1, int(self.cvm_set_no) + 1):
                paper_corpus = {}
                for rec in d_unreserved:
                    dq_list = d_unreserved[rec]['qid']
                    u_count = d_unreserved[rec]['count']
                    if len(dq_list) >= u_count:
                        t_list = random.sample(dq_list, u_count)
                        up_list = [i for i in dq_list if i not in t_list]
                        d_unreserved.update({rec: {'qid': up_list, 'count': u_count}})
                        r_list = reserved[rec]['qid']
                        t_list.extend(r_list)
                        paper_corpus.update({rec: t_list})
                    else:
                        diff = u_count - len(dq_list)
                        if diff == u_count:
                            un_list = unreserved[rec]['qid']
                            b_list = un_list
                            t_list = random.sample(b_list, u_count)
                            up_list = [i for i in dq_list if i not in t_list]
                            d_unreserved.update({rec: {'qid': up_list, 'count': u_count}})
                            r_list = reserved[rec]['qid']
                            t_list.extend(r_list)
                            paper_corpus.update({rec: t_list})
                        else:
                            un_list = unreserved[rec]['qid']
                            b_list = [i for i in un_list if i not in dq_list]
                            b_list = random.sample(b_list, diff)
                            dq_list.extend(b_list)
                            t_list = random.sample(dq_list, u_count)
                            up_list = [i for i in dq_list if i not in t_list]
                            d_unreserved.update({rec: {'qid': up_list, 'count': u_count}})
                            r_list = reserved[rec]['qid']
                            t_list.extend(r_list)
                            paper_corpus.update({rec: t_list})
                for variant in range(1, int(self.cvm_version_no) + 1):
                    random.shuffle(set)
                    paper_id = str(self.cvm_design_version_id) + str(paper).zfill(2) + str(variant).zfill(2)
                    paper_question_list = []
                    random.shuffle(subject_list)
                    for k in subject_list:
                        set_list = subject_d.get(k)
                        random.shuffle(set_list)
                        for j in set_list:
                            shuffle_list = paper_corpus.get(j)
                            random.shuffle(shuffle_list)
                            paper_question_list.extend(shuffle_list)
                    if len(paper_question_list) < self.cvm_total_questions:
                        raise ValidationError("Error while generating paper,please raise the ticket")
                    else:
                        pass
                    # print('paper_id', paper_id)
                    # print('paper_question_list',paper_question_list)
                    # print('paper', paper)
                    # print('variant', variant)
                    # print('schedule_id', self.cvm_design_id.schedule_id)
                    # print('exam_name', self.cvm_design_id.exam_name)
                    # print('before_my_sql')
                    self.env['question.paper.details'].create({
                        'qpd_schedule_id': self.cvm_design_id.schedule_id,
                        'qpd_paper_id': paper_id,
                        'qpd_q_ids':paper_question_list,
                        'qpd_total_time': self.cvm_total_time,
                        'qpd_total_questions': self.cvm_total_questions,
                        'created_by': self.env.uid,
                        'updated_by': self.env.uid,
                        'qpd_title': self.cvm_design_id.exam_name,
                    })

                    # if self.cvm_is_1_n == 1:
                    #     conn = mysql.connector.connect(host='',
                    #                                    password='', user='', port=3306, database='tnschools_working')
                    #     cursor = conn.cursor()
                    #     sql = "insert into tnschools_working.version_questions(cvp_event_id,cvp_paper_id,cvp_q_id,pa_total_q,pa_total_time,participant_pk,author_id) values(%s,%s,%s,%s,%s,%s,%s);"
                    #     val = (self.cvm_event_details.schedule_id, paper_id, str(paper_question_list),
                    #            self.cvm_total_questions,
                    #            self.cvm_total_time, participant_pk, self.create_uid.login)
                    # if self.cvm_is_1_n == 0:
                    #     conn = mysql.connector.connect(host='',
                    #                                    password='', user='', port=3306, database='tnschools_working')
                    #     cursor = conn.cursor()
                    #     sql = "insert into tnschools_working.version_questions(cvp_event_id,cvp_paper_id,cvp_q_id,pa_total_q,pa_total_time,author_id) values(%s,%s,%s,%s,%s,%s);"
                    #     val = (self.cvm_event_details.schedule_id, paper_id, str(paper_question_list),
                    #            self.cvm_total_questions,
                    #            self.cvm_total_time, self.create_uid.login)
                    # cursor.execute(sql, val)
                    # conn.commit()
                    # query = sql % val
                    # print(query)
                    paper_version.append((0, 0,
                                          {"cvp_paper_number": paper, "cvp_variant_number": variant,
                                           "cvp_q_id": paper_question_list,
                                           "cvp_paper_version_id": self.cvm_design_version_id, "cvp_paper_id": paper_id,
                                           "cvp_total_q": self.cvm_total_questions,
                                           "cvp_total_time": self.cvm_total_time}))
            self.env['version.master'].browse(self.id).write({'cvm_paper_version': paper_version})

        self.allocation_start()
        return
#############################view_paper####################################
    def view_paper(self):
        query = """
            SELECT 
	    qpd.qpd_paper_id,
    qmt.qmt_question_code, 
    qmt.qmt_q_text,
   	qat.qat_option1,
	qat.qat_option2,
	qat.qat_option3,
	qat.qat_option4,
	qat.qat_correct_answer
FROM 
    question_paper_details qpd
CROSS JOIN LATERAL 
    unnest(string_to_array(regexp_replace(regexp_replace(qpd.qpd_q_ids, '\[|\]', '', 'g'), '''', '', 'g'), ',')) AS question_id
LEFT JOIN 
    question_master_table qmt
    ON qmt.qmt_question_code = CAST(question_id AS INTEGER)
JOIN question_answer_table qat
	ON qat.qat_question_code = qmt.qmt_question_code
WHERE 
    qpd.qpd_schedule_id = %s
    ORDER BY qpd.qpd_paper_id;
        """
        self.env.cr.execute(query, (self.cvm_design_id.schedule_id,))
        results = self.env.cr.fetchall()
        print('self',self)
        print('self', self.cvm_design_id)
        print('exam_name', self.cvm_design_id.exam_name)
        print('subject_name', self.cvm_design_id.subject.smt_subject_name)
        print('standard_dropdown', self.cvm_design_id.standard_dropdown)
        print('medium', self.cvm_design_id.subject.smt_medium_id.mmt_medium_name)
        print('schedule_id', self.cvm_design_id.schedule_id)

        # self.env['question.paper.line'].search([]).unlink()
        # self.env['question.paper.id.line'].search([]).unlink()

        for result in results:
            question_paper_id_line_id = self.env['question.paper.id.line'].search([('paper_id', '=', result[0])],
                                                                                  limit=1)
            if not question_paper_id_line_id:
                question_paper_id_line_id = self.env['question.paper.id.line'].create({
                    'paper_id': result[0],
                    'version_master_id': self.id,
                    'exam_name': self.cvm_design_id.exam_name,
                    'subject_name': self.cvm_design_id.subject.smt_subject_name,
                    'standard_dropdown': self.cvm_design_id.standard_dropdown,
                    'medium': self.cvm_design_id.subject.smt_medium_id.mmt_medium_name,
                    'schedule_id': self.cvm_design_id.schedule_id
                })

        # Insert fetched data into `question.paper.line`
        for result in results:
            question_paper_id_line_id = self.env['question.paper.id.line'].search([('paper_id', '=', result[0])],
                                                                                  limit=1)
            self.env['question.paper.line'].create({
                'paper_id': result[0],
                'question_code': result[1],
                'question_text': result[2],
                'option1': result[3],
                'option2': result[4],
                'option3': result[5],
                'option4': result[6],
                'correct_answer': result[7],
                'qp_id_line_id': question_paper_id_line_id.id,
            })

        # Return an action to open the `question.paper.line` view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Question Paper ID',
            'view_mode': 'tree',
            'res_model': 'question.paper.id.line',
            'flags': {'hasSelectors': False},
            'domain': [('version_master_id', '=', self.id)],
            'target': 'current',
        }

    #############################view_paper ends ####################################
    #############################print_paper starts #################################
#     def print_paper(self):
#         print("Executing print_paper method...", self.cvm_design_id.schedule_id)
#         query = """
#             SELECT
# 	qpd.qpd_paper_id,
#     qmt.qmt_question_code,
#     qmt.qmt_q_text,
#    	qat.qat_option1,
# 	qat.qat_option2,
# 	qat.qat_option3,
# 	qat.qat_option4
# FROM
#     question_paper_details qpd
# CROSS JOIN LATERAL
#     unnest(string_to_array(regexp_replace(regexp_replace(qpd.qpd_q_ids, '\[|\]', '', 'g'), '''', '', 'g'), ',')) AS question_id
# LEFT JOIN
#     question_master_table qmt
#     ON qmt.qmt_question_code = CAST(question_id AS INTEGER)
# JOIN question_answer_table qat
# 	ON qat.qat_question_code = qmt.qmt_question_code
# WHERE
#     qpd.qpd_schedule_id = %s;
#         """
#         self.env.cr.execute(query, (self.cvm_design_id.schedule_id,))
#         results = self.env.cr.fetchall()
#
#         # Clear existing data in `question.paper.line`
#         self.env['question.paper.line'].search([]).unlink()
#
#         # Insert fetched data into `question.paper.line`
#         for result in results:
#             print('result', result)
#             self.env['question.paper.line'].create({
#                 'paper_id': result[0],
#                 'question_code': result[1],
#                 'question_text': result[2],
#                 'option1' :result[3],
#                 'option2': result[4],
#                 'option3': result[5],
#                 'option4': result[6],
#             })
#
#         # Return an action pdf
#         return self.env.ref('education_exam.q_paper_action_id').report_action(self)

    #############################print_paper ends #################################
    def allocation_start(self):
        total_papers = int(self.cvm_set_no) * int(self.cvm_version_no)
        for rec in self:
            rec.cvm_paper_allocation.unlink()
        # is_1_n=self.cvm_event_details.is_1_n
        # conn = mysql.connector.connect(host='',
        #                                password='', user='', port=3306, database='tnschools_working')
        # participant_type_query = "select  distinct(participant_category) from tnschools_working.scheduler_participants where schedule_id_id={};".format(
        #     self.cvm_event_details.schedule_id)
        # cursor = conn.cursor()
        # cursor.execute(participant_type_query)
        # participant_type_query_response = cursor.fetchall()
        #
        # participant_type = participant_type_query_response[0][0]
        # if self.cvm_is_1_n == 0:
        #     if participant_type == 'DISTRICT':
        #
        #         partcipant_query = """select  distinct participant_category,district_id,district_name from tnschools_working.scheduler_participants  left join
        #                        tnschools_working.students_school_child_count on participant_id=district_id where schedule_id_id={};""".format(
        #             self.cvm_event_details.schedule_id)
        #         cursor = conn.cursor()
        #
        #         try:
        #             dl_code = 'PD'
        #             query_start = time.time()
        #             cursor.execute(partcipant_query)
        #         except:
        #             raise UserError("Database is not responding please try after sometime.")
        #         partcipant_query_response = cursor.fetchall()
        #         cursor.close()
        #         now = time.time()
        #         db_logs_create = self.env['db.logs'].create(
        #             {'dl_id': self.cvm_design_version_id, 'dl_code': dl_code, 'dl_time': (now - query_start)})
        #         if not partcipant_query_response:
        #             raise ValidationError("No participants details found for given event.")
        #
        #     elif participant_type == 'SCHOOL':
        #
        #         partcipant_query = """select  participant_category,participant_id,school_name from tnschools_working.scheduler_participants inner join
        #                        tnschools_working.students_school_child_count on participant_id=school_id where schedule_id_id={};""".format(
        #             self.cvm_event_details.schedule_id)
        #         cursor = conn.cursor()
        #         try:
        #             dl_code = 'PS'
        #             query_start = time.time()
        #             cursor.execute(partcipant_query)
        #         except:
        #             raise UserError("Database is not responding please try after sometime.")
        #         partcipant_query_response = cursor.fetchall()
        #         cursor.close()
        #         now = time.time()
        #         db_logs_create = self.env['db.logs'].create(
        #             {'dl_id': self.cvm_design_version_id, 'dl_code': dl_code, 'dl_time': (now - query_start)})
        #         if not partcipant_query_response:
        #             raise ValidationError("No participants details found for given event.")
        #     allocation_list = []
        #     # if participant_type == 'DISTRICT' or participant_type == 'SCHOOL':
        #     for rec in partcipant_query_response:
        #         allocation_list.append(
        #             (0, 0,
        #              {"pa_participant_category": rec[0], "pa_participant_id": rec[1],
        #               "pa_participant_name": rec[2],
        #               "pa_paper_count": total_papers, "pa_variant_count": int(self.cvm_set_no)}))
        # if self.cvm_is_1_n == 1:
        #     partcipant_query = """select  participant_category,participant_id,school_name,section from scheduler_participants ss inner join
        #                        students_school_child_count sscc on participant_id=school_id where schedule_id_id={} and ss.id={};""".format(
        #         self.cvm_event_details.schedule_id, self.cvm_design_id.participant_pk)
        #     cursor = conn.cursor()
        #     try:
        #         dl_code = 'PS'
        #         query_start = time.time()
        #         cursor.execute(partcipant_query)
        #     except:
        #         raise UserError("Database is not responding please try after sometime.")
        #     partcipant_query_response = cursor.fetchall()
        #     cursor.close()
        #     now = time.time()
        #     db_logs_create = self.env['db.logs'].create(
        #         {'dl_id': self.cvm_design_version_id, 'dl_code': dl_code, 'dl_time': (now - query_start)})
        #     if not partcipant_query_response:
        #         raise ValidationError("No participants details found for given event.")
        #     allocation_list = []
        #     for rec in partcipant_query_response:
        #         allocation_list.append(
        #             (0, 0,
        #              {"pa_participant_category": rec[0], "pa_participant_id": rec[1],
        #               "pa_participant_name": rec[2], "pa_class_section": rec[3],
        #               "pa_paper_count": total_papers, "pa_variant_count": int(self.cvm_set_no)}))
        #
        # self.env['version.master'].browse(self.id).write({'cvm_paper_allocation': allocation_list})
        # self.cvm_state = 'als'
        return

    def allocate(self):
        if self.cvm_state == 'cnf':
            raise UserError('Allocation already completed.')
        # paper_corpus = {}
        for rec in self.cvm_paper_allocation:
            if rec.pa_paper_count == 0 or rec.pa_variant_count == 0:
                raise UserError('Please enter value greater than 0')
        # print(len(self.cvm_paper_allocation))
        no_participant = len(self.cvm_paper_allocation)
        if no_participant < 1:
            raise UserError('No participant found')
        if self.cvm_is_1_n == 0:
            # print('Normal Event')
            participant_paper_list = self.cvm_paper_version.mapped('cvp_paper_id')
            # print(participant_paper_list)
            for rec in self.cvm_paper_allocation:
                update = (1, rec.id, {"pa_paper_id": participant_paper_list, })
                self.env['version.master'].browse(self.id).write({'cvm_paper_allocation': [update]})
            self.cvm_event_details.allocation_status = 1

            # print(self.cvm_event_details.allocation_status)
            ###MYSQL insert
            conn = mysql.connector.connect(host='',
                                           password='', user='', port=3306, database='tnschools_working')
            cursor = conn.cursor()
            # sql_allocation = "update tnschools_working.scheduler_participants set event_allocationid=%s ,allocation_status=%s , allocated_by=%s where schedule_id_id=%s;"
            # val = (str(participant_paper_list), 1, self.create_uid.login, self.cvm_event_details.schedule_id)
            ###proposed method
            sql_allocation = "update tnschools_working.scheduler_participants set event_allocationid=%s ,allocation_status=%s , allocated_by=%s where schedule_id_id=%s;"
            val = (
                self.cvm_paper_allocation[0].pa_paper_id, 1, self.create_uid.login, self.cvm_event_details.schedule_id)
            cursor.execute(sql_allocation, val)
            query = sql_allocation % val

            query_registry_id = self.env['query.registry'].create(
                {'version_id': self.cvm_design_version_id,
                 'query_text': query})
            conn.commit()
            cursor = conn.cursor()
            sql_allocation_flag = "update tnschools_working.scheduler_scheduling set event_allocationid=%s where schedule_id=%s;"
            val_flag = (1, self.cvm_event_details.schedule_id)
            cursor.execute(sql_allocation_flag, val_flag)
            conn.commit()
            ############# Paper Generation API Call ###################
            url = "https://websiteurl&eventid={}&username={}".format(
                self.cvm_event_details.schedule_id, self.create_uid.login)
            payload = {}
            headers = {}
            response = requests.request("POST", url, headers=headers, data=payload)

        elif self.cvm_is_1_n == 1:
            participant_paper_list = self.cvm_paper_version.mapped('cvp_paper_id')
            update = (1, rec.id, {"pa_paper_id": participant_paper_list, })
            self.env['version.master'].browse(self.id).write({'cvm_paper_allocation': [update]})
            # print(self.cvm_allocation_status)
            ###MYSQL insert
            conn = mysql.connector.connect(host='',
                                           password='', user='', port=3306, database='tnschools_working')
            cursor = conn.cursor()
            sql_allocation = "update tnschools_working.scheduler_participants set event_allocationid=%s ,allocation_status=%s ," \
                             " allocated_by=%s where schedule_id_id=%s and  id=%s;"
            val = (self.cvm_paper_allocation.pa_paper_id, 1, self.create_uid.login, self.cvm_event_details.schedule_id,
                   self.cvm_design_id.participant_pk)
            # sql_allocation = "update tnschools_working.scheduler_participants set event_allocationid=%s ,allocation_status=%s ," \
            #                  " allocated_by=%s where schedule_id_id=%s and  id=%s;"
            # val = (str(participant_paper_list), 1, self.create_uid.login, self.cvm_event_details.schedule_id,
            #        self.cvm_design_id.participant_pk)
            cursor.execute(sql_allocation, val)
            query = sql_allocation % val
            # print(query)
            conn.commit()
            query_registry_id = self.env['query.registry'].create(
                {'participant_pk': self.cvm_design_id.participant_pk, 'version_id': self.cvm_design_version_id,
                 'query_text': query})

            if self.cvm_event_details.allocation_status != 1:
                self.cvm_event_details.allocation_status = 1
                cursor = conn.cursor()
                sql_allocation_flag = "update tnschools_working.scheduler_scheduling set event_allocationid=%s where schedule_id=%s;"
                val_flag = (1, self.cvm_event_details.schedule_id)
                cursor.execute(sql_allocation_flag, val_flag)
                query = sql_allocation_flag % val_flag
                # print(query)
                conn.commit()
            ############# Paper Generation API Call ###################

            url = "https://websiteurl&eventid={}&username={}&participant_pk={}".format(
                self.cvm_event_details.schedule_id, self.create_uid.login, self.cvm_design_id.participant_pk)

            payload = {}
            headers = {}
            response = requests.request("POST", url, headers=headers, data=payload)

        self.cvm_state = 'cnf'

        id_process = self.env['id.process'].create({'design_id': self.cvm_design_id,
                                                    'version_id': self.id})

        if response.status_code == 200:
            return {
                'effect': {
                    'fadeout': 'fast',
                    'message': 'Allocation completed,please close the tab now.',
                    'type': 'rainbow_man',
                }
            }
        else:
            return {
                'effect': {
                    'fadeout': 'fast',
                    'message': 'Allocation completed.',
                    'type': 'rainbow_man',
                }
            }


class VersionSummary(models.Model):
    _name = 'version.set.summary'
    _description = 'Version summary'
    _rec_name = ''
    cvs_set_no = fields.Integer('Group number')
    cvs_av_qs = fields.Integer('Available questions')
    cvs_in_qs = fields.Integer(string='Questions to insert')
    cvs_desc = fields.Char(string='Group Description')
    cvs_sec = fields.Char(string='Group Section(Optional)')
    cvs_design_version_id = fields.Many2one('version.master', string='Version ID')
    cvs_difficulty = fields.Integer(string="Difficulty")
    cvs_chapter_id = fields.Integer(string="Chapter ID")
    cvs_difficulty_text = fields.Char(string='Difficulty Level', compute='_compute_qc_difficulty')
    # cvs_subject_id = fields.Many2one('question.subject', string='Subject')
    cvs_subject_id = fields.Integer(string='Subject')
    cvs_subject_name = fields.Char(string='Subject Name')
    cvs_standard = fields.Char(string='Standard')

    @api.depends('cvs_difficulty')
    def _compute_qc_difficulty(self):
        for q in self:
            if q.cvs_difficulty == 1:
                q.cvs_difficulty_text = 'Easy'
            elif q.cvs_difficulty == 2:
                q.cvs_difficulty_text = 'Medium'
            else:
                q.cvs_difficulty_text = 'Hard'


class paper_allocation(models.Model):
    _name = 'paper.allocation'
    _description = 'Paper Allocation'
    _rec_name = ''
    pa_event_id = fields.Char('Event ID')
    pa_participant_category = fields.Char('Participant Category')
    pa_participant_id = fields.Integer('Participant ID')
    pa_participant_name = fields.Char('Participant Name')
    pa_paper_count = fields.Integer('Total no. of papers')
    pa_variant_count = fields.Integer('No. of sets')
    pa_paper_id = fields.Char('Paper ID')
    pa_design_version_id = fields.Many2one('version.master', string='Version ID')
    pa_class_section = fields.Char('Class Section')


class VersionPaperQuestion(models.Model):
    _name = 'version.paper.question'
    _description = 'Version summary'
    _rec_name = ''
    cvp_paper_number = fields.Integer('Paper number')
    cvp_variant_number = fields.Integer('Variant Number')
    cvp_order = fields.Integer('Order Number')
    cvp_q_id = fields.Char('Paper ID')
    cvp_design_version_id = fields.Many2one('version.master', string='Version ID')
    cvp_paper_version_id = fields.Char("Version ID")
    cvp_paper_id = fields.Char("Paper ID")
    cvp_total_q = fields.Integer("Total Questions")
    cvp_total_time = fields.Integer("Total Time")


class ScheduleDetails(models.Model):
    _name = 'schedule.details'
    _description = 'Schedule Details'
    _rec_name = 'event_title'
    schedule_id = fields.Integer('Schedule ID')
    schedule_type = fields.Integer('Schedule Type')
    class_std = fields.Integer('Standard')
    event_startdate = fields.Date('Event Start Date')
    event_title = fields.Char('Event Title')
    event_approval_status = fields.Char('Event Approval Status')
    design_version_id = fields.Many2one('version.master', string='Version ID')
    allocation_status = fields.Integer(string='Allocation Status')
    cdac_schedule_create_id = fields.Integer(string='CDAC Schedule Author id')
    medium = fields.Integer('Medium')
    # schedule_subject=fields.Integer('Subject')
    schedule_subject = fields.Many2one('question.subject', string='Subject*')
    is_1_n = fields.Integer(string='Flow category')

    # flag1 to denote JEE/NEET; For JEE, flag1=7 and NEET, flag1=8;otherwise NULL
    flag1 = fields.Integer('Flag1')
    class_group = fields.Integer('Group')


class EducationSubject(models.Model):
    _name = 'question.subject'
    _description = 'Question Subject'
    _rec_name = 'subject_name'
    subject_name = fields.Char(string='Subject')
    subject_code = fields.Integer(string='Subject Code')
    standard = fields.Integer(string='Standard')
    stream = fields.Char('Stream')
    design_id = fields.Many2one('education.exam', string='Design ID')

    # is_active = fields.Boolean(string="Is Active")


class EducationSubjectChapter(models.Model):
    _name = 'question.subject.chapter'
    _description = 'Chapter name'
    _rec_name = 'chapter_idx_id'
    checkbox = fields.Boolean(string="Checkbox", default=False)
    chapter_id = fields.Integer(string='Chapter ID')
    chapter_name = fields.Char("Chapter Name", readonly=True, required=True)
    set_id = fields.Many2one('education.exam', string='Set ID')
    is_active = fields.Boolean(string="Is Active")
    chapter_idx_id = fields.Integer(string='Taxonomy chapter ID')
    q_count_chapter = fields.Integer(string='Question Count')

    def name_get(self):
        result = []
        for rec in self:
            name = str(rec.chapter_id) + '-' + str(rec.chapter_name)
            result.append((rec.id, name))
        return result


class StandardGroupCode(models.Model):
    _name = 'group.code'
    _description = 'Stream'
    _rec_name = 'group_name'
    group_code_id = fields.Char('Group Code')
    group_name = fields.Char('Group Name')
    design_id = fields.Many2one('education.exam', string='Design ID')

    def name_get(self):
        result = []
        for rec in self:
            name = str(rec.group_code_id) + ' - ' + str(rec.group_name)
            result.append((rec.id, name))
        return result


class EducationDifficulty(models.Model):
    _name = 'question.difficulty'
    _description = 'Question Difficulty'
    _rec_name = 'difficulty_id'
    difficulty_id = fields.Char(string='Difficulty')
    is_active = fields.Boolean(string="Is Active")


class SetSection(models.Model):
    _name = 'set.section'
    _description = 'Set Section'
    _rec_name = 'setsection_id'
    setsection_id = fields.Char(string='Set Section')
    is_active = fields.Boolean(string="Is Active")


class QuestionMark(models.Model):
    _name = 'question.mark'
    _description = 'Question Mark'
    _rec_name = 'mark_id'
    mark_id = fields.Char(string='Marks')
    is_active = fields.Boolean(string="Is Active")


class QuestionStandard(models.Model):
    _name = 'question.standard'
    _description = 'Question Standard'
    _rec_name = 'standard_id'
    standard_id = fields.Char(string='Standard')
    is_active = fields.Boolean(string="Is Active")


class ChapterList(models.Model):
    _name = 'chapter.list'
    _description = 'Chapter List'
    _rec_name = 'cl_chapter_name'
    cl_chapter_idx = fields.Integer(string='Chapter IDX')
    cl_chapter_name = fields.Char(string='Chapter Name')
    cl_chapter_id = fields.Integer(string='Chapter Number')
    cl_medium_id = fields.Integer(string='Medium')
    cl_standard = fields.Integer(string='Standard')
    cl_subject_id = fields.Integer(string='Subject')
    cl_term_id = fields.Integer(string='Term')
    set_id = fields.Many2one('education.exam', string='Set ID')


class TopicList(models.Model):
    _name = 'topic.list'
    _description = 'Topic List'
    _rec_name = 'tl_topic_name'
    tl_topic_idx = fields.Integer(string='Topic IDX')
    tl_topic_name = fields.Char(string='Topic name')
    tl_chapter_idx = fields.Integer(string='Chapter IDX')
    set_id = fields.Many2one('education.exam', string='Set ID')
    tl_standard = fields.Integer(string='Standard')
    tl_medium = fields.Integer(string='Medium')
    tl_term_id = fields.Integer(string='Term')
    tl_subject_id = fields.Integer(string='Subject')


class QuestionList(models.Model):
    _name = 'question.list'
    _description = 'Question List'
    _rec_name = 'ql_name'
    checkbox = fields.Boolean(string="Checkbox", default=False)
    ql_criteria = fields.Integer('Selection Criteria')
    ql_criteria_name = fields.Char('Criteria')
    ql_idx_id = fields.Integer('IDX ID')
    ql_name = fields.Char('Name')
    ql_medium = fields.Integer('Medium')
    ql_standard = fields.Integer('Standard')
    ql_subject = fields.Integer('Subject')
    ql_chapter_idx_id = fields.Integer('Chapter IDX ID')
    ql_topic_idx_id = fields.Integer('Topic IDX ID')
    ql_q_count = fields.Integer('Question Count')
    ql_term = fields.Integer('Term')
    ql_chapter = fields.Char('Chapter')
    set_id = fields.Many2one('education.exam', string='Set ID')
    # jeeneet
    ql_difficulty = fields.Integer('Difficulty')


class DbLogs(models.Model):
    _name = 'db.logs'
    _description = 'DB Logs'
    _rec_name = 'dl_code'
    dl_id = fields.Char('Design/Version ID')
    dl_code = fields.Char('Code')
    # dl_user=fields.Char('User ID')
    dl_time = fields.Float('Response Time')


class IdProcess(models.Model):
    _name = 'id.process'
    _description = 'ID Process'
    _rec_name = ''
    design_id = fields.Integer('Design ID')
    version_id = fields.Integer('Version ID')


class QueryRegistry(models.Model):
    _name = 'query.registry'
    _description = ' Query Registry'
    _rec_name = ''
    participant_pk = fields.Integer('Participant ID')
    version_id = fields.Char('Version ID')
    query_text = fields.Text('Query')


##################### qp tool new models #########################

class MediumMasterTable(models.Model):
    _name = 'medium.master.table'
    _description = 'Medium Master Table'
    _rec_name = 'mmt_medium_name'

    mmt_medium_code = fields.Integer(string='Medium Code', required=True)
    mmt_medium_name = fields.Char(string='Medium Name', required=True)
    is_active = fields.Boolean(string="Is Active")

    _sql_constraints = [
        ('unique_mmt_medium_code', 'UNIQUE(mmt_medium_code)', 'Medium Code must be unique!')
    ]

class SubjectMasterTable(models.Model):
    _name = 'subject.master.table'
    _description = 'Subject Master Table'
    _rec_name = 'smt_subject_name'

    smt_subject_code = fields.Integer(string='Subject Code', required=True)
    smt_subject_name = fields.Char(string='Subject Name', required=True)
    smt_medium_id = fields.Many2one('medium.master.table', string='Medium', required=True)
    smt_medium_code = fields.Integer(string='Medium Code', related='smt_medium_id.mmt_medium_code', store=True)
    smt_created_date = fields.Date(string='Created Date')
    smt_updated_date = fields.Date(string='Created Date')
    smt_is_active = fields.Boolean(string="Is Active")
    smt_standard = fields.Integer(string='Standard', required=True)

    _sql_constraints = [
        ('unique_smt_subject_code', 'UNIQUE(smt_subject_code)', 'Subject Code must be unique!')
    ]

class SubjectTaxonomyMaster(models.Model):
    _name = 'subject.taxonomy.master'
    _description = 'Subject Taxonomy Master'
    _rec_name = ''

    stm_taxonomy_code = fields.Integer(string='Taxonomy Code', required=True)
    stm_subject_id = fields.Many2one('subject.master.table', string='Subject')
    stm_subject_code = fields.Integer(string='Subject Code', related='stm_subject_id.smt_subject_code', store=True)
    stm_chapter_code = fields.Integer(string='Chapter Code', required=True)
    stm_chapter_name = fields.Char(string='Chapter Name', required=True)
    stm_topic_code = fields.Integer(string='Chapter Code', required=True)
    stm_topic_name = fields.Char(string='Chapter Name', required=True)
    stm_standard = fields.Integer(string='Standard', required=True)
    stm_medium_id = fields.Many2one('medium.master.table', string='Medium', required=True)
    stm_medium_code = fields.Integer(string='Medium Code', related='stm_medium_id.mmt_medium_code', store=True)
    stm_created_date = fields.Date(string='Created Date')
    stm_updated_date = fields.Date(string='Created Date')
    stm_is_active = fields.Boolean(string="Is Active")


    _sql_constraints = [
        ('unique_taxonomy_codestm_taxonomy_code', 'UNIQUE(stm_taxonomy_code)', 'Taxonomy Code must be unique!')
    ]

class QuestinTypeMaster(models.Model):
    _name = 'question.type.master'
    _description = 'Questin Type Master'
    _rec_name = 'qtm_type_name'

    qtm_type_code = fields.Integer(string='Question Type Code', required=True)
    qtm_type_name = fields.Char(string='Question Type Name', required=True)
    qtm_is_active = fields.Boolean(string="Is Active")

    _sql_constraints = [
        ('unique_q_type_code', 'UNIQUE(q_type_code)', 'Question Type Code must be unique!')
    ]

class QuestinFormatMaster(models.Model):
    _name = 'question.format.master'
    _description = 'Questin Format Master'
    _rec_name = 'qfm_format_name'

    qfm_format_code = fields.Integer(string='Question Format Code', required=True)
    qfm_format_name = fields.Char(string='Question Format Name', required=True)
    qfm_active = fields.Boolean(string="Is Active")

    _sql_constraints = [
        ('unique_q_format_code', 'UNIQUE(q_format_code)', 'Question Format Code must be unique!')
    ]

class QuestionMasterTable(models.Model):
    _name = 'question.master.table'
    _description = 'Question Master Table'
    _rec_name = ''

    qmt_question_code = fields.Integer(string='Question Code', required=True)
    qmt_type_id = fields.Many2one('question.type.master', string='Q Type')
    qmt_type_code = fields.Integer(string='Q Type Code', related='qmt_type_id.qtm_type_code', store=True)
    qmt_format_id = fields.Many2one('question.format.master', string='Q Format')
    qmt_format_code = fields.Integer(string='Q Format Code', related='qmt_format_id.qfm_format_code', store=True)
    qmt_taxonomy_id = fields.Many2one('subject.taxonomy.master', string='Taxonomy')
    qmt_taxonomy_code = fields.Integer(string='Taxonomy Code', related='qmt_taxonomy_id.stm_taxonomy_code', store=True)
    qmt_q_text = fields.Char(string='Question Text', required=True)
    qmt_marks = fields.Integer(string='Marks', required=True)
    qmt_created_date = fields.Date(string='Created Date')
    qmt_updated_date = fields.Date(string='Created Date')
    qmt_is_active = fields.Boolean(string="Is Active")


    _sql_constraints = [
        ('unique_qmt_question_code', 'UNIQUE(qmt_question_code)', 'Question Code must be unique!')
    ]

class QuestionAnswerTable(models.Model):
    _name = 'question.answer.table'
    _description = 'Question Answer Table'
    _rec_name = ''

    qat_question_id = fields.Many2one('question.master.table')
    qat_question_code = fields.Integer(string='Question Code', related='qat_question_id.qmt_question_code', store=True)
    qat_option1 = fields.Char(string='Option 1')
    qat_option2 = fields.Char(string='Option 2')
    qat_option3 = fields.Char(string='Option 3')
    qat_option4 = fields.Char(string='Option 4')
    qat_correct_answer = fields.Char(string='Correct Answer', required=True)
    qat_type_id = fields.Many2one('question.type.master', string='Q Type')
    qat_type_code = fields.Integer(string='Q Type Code', related='qat_type_id.qtm_type_code', store=True)


class QuestionPaperDetails(models.Model):
    _name = 'question.paper.details'
    _description = 'Question Paper Details'

    # qpd_schedule_id = fields.Integer(string="Schedule ID")
    qpd_schedule_id = fields.Char(string="Schedule ID")
    qpd_paper_id = fields.Char(string="Paper ID")
    qpd_q_ids = fields.Char(string="Question IDs")
    qpd_total_time = fields.Integer(string="Total Time (minutes)")
    qpd_total_questions = fields.Integer(string="Total Questions")
    created_by = fields.Many2one('res.users', string="Created By")
    updated_by = fields.Many2one('res.users', string="Updated By")
    qpd_title = fields.Char(string="Title")

class QuestionPaperIdLine(models.Model):
    _name = 'question.paper.id.line'
    _description = 'Question Paper ID Line'

    paper_id = fields.Char(string="Question Paper ID")
    version_master_id = fields.Many2one('version.master', Text='Version Master ID')
    exam_name = fields.Char(string="Exam Name")
    subject_name = fields.Char(string="Subject Name")
    standard_dropdown = fields.Char(string="Standard")
    medium = fields.Char(string="Medium")
    schedule_id = fields.Char(string="Schedule ID")

    _sql_constraints = [
        ('unique_paper_id', 'unique(paper_id)', 'The QP Schedule ID must be Paper Id.')
    ]

    def action_view_questions(self):
        """Action to generate the question paper report."""
        domain = [('paper_id', '=', self.paper_id)]
        question_lines = self.env['question.paper.line'].search(domain)
        return self.env.ref('education_exam.q_paper_line_id').report_action(question_lines)

    def action_view_questions_answer(self):
        """Action to generate the question answer report."""
        domain = [('paper_id', '=', self.paper_id)]
        question_lines = self.env['question.paper.line'].search(domain)
        return self.env.ref('education_exam.q_ans_paper_line_id').report_action(question_lines)

    def action_view_questions_template(self):
        """Render the question paper in a QWeb template view for viewing."""
        # Ensure 'paper_id' is available and valid
        if not self.paper_id:
            raise UserError('No Paper ID specified.')

        # Search for the related question lines
        domain = [('paper_id', '=', self.paper_id)]
        question_lines = self.env['question.paper.line'].search(domain)

        print(question_lines)

        if not question_lines:
            raise UserError('No questions found for the selected Paper ID.')

        # Return the report action, rendering the template for the question lines
        return self.env.ref('education_exam.q_paper_line_view_id').report_action(question_lines)


class QuestionPaperLine(models.Model):
    _name = 'question.paper.line'
    _description = 'Question Paper Line'

    paper_id = fields.Char(string="Paper")
    question_code = fields.Char(string="Question Code")
    question_text = fields.Text(string="Question Text")
    option1 = fields.Char(string="option1")
    option2 = fields.Char(string="option2")
    option3 = fields.Char(string="option3")
    option4 = fields.Char(string="option4")
    correct_answer = fields.Char(string="Correct Answer")
    qp_id_line_id = fields.Many2one('question.paper.id.line', Text='Question Paper Id Line Id')

class DashKanban(models.Model):
    _name = 'dash.kanban'
    _description = 'Dash Kanban'

    name = fields.Char(string="Name")

    def design_paper_view(self):
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Design Paper',
            'view_mode': 'tree,form',
            'res_model': 'education.exam',
            'domain': [] if is_admin else [('create_uid', '=', user.id)],
        }

    def design_paper_create(self):
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Design Paper',
            'view_mode': 'form',
            'res_model': 'education.exam',
            'domain': [] if is_admin else [('create_uid', '=', user.id)],
        }
    def view_question_paper(self):
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Question Paper',
            'view_mode': 'tree',
            'res_model': 'question.paper.id.line',
            'domain': [] if is_admin else [('create_uid', '=', user.id)],
        }


