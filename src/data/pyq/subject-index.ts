// Generated from the supplied INICET edition by scripts/pyq/populate.py.
import type { Subject } from '../types';
import type { PaperYear } from './index';
import anatomy from './subjects/anatomy';
import physiology from './subjects/physiology';
import biochemistry from './subjects/biochemistry';
import pathology from './subjects/pathology';
import pharmacology from './subjects/pharmacology';
import microbiology from './subjects/microbiology';
import forensic_medicine from './subjects/forensic-medicine';
import psm from './subjects/psm';
import ent from './subjects/ent';
import ophthalmology from './subjects/ophthalmology';
import general_medicine from './subjects/general-medicine';
import general_surgery from './subjects/general-surgery';
import obstetrics_gynaecology from './subjects/obstetrics-gynaecology';
import pediatrics from './subjects/pediatrics';
import orthopedics from './subjects/orthopedics';
import dermatology from './subjects/dermatology';
import psychiatry from './subjects/psychiatry';
import radiology from './subjects/radiology';
import anesthesia from './subjects/anesthesia';

export const subjectIndex: Record<Subject, Record<PaperYear, number[][]>> = {
  "Anatomy": anatomy,
  "Physiology": physiology,
  "Biochemistry": biochemistry,
  "Pathology": pathology,
  "Pharmacology": pharmacology,
  "Microbiology": microbiology,
  "Forensic Medicine": forensic_medicine,
  "PSM": psm,
  "ENT": ent,
  "Ophthalmology": ophthalmology,
  "General Medicine": general_medicine,
  "General Surgery": general_surgery,
  "Obstetrics & Gynaecology": obstetrics_gynaecology,
  "Pediatrics": pediatrics,
  "Orthopedics": orthopedics,
  "Dermatology": dermatology,
  "Psychiatry": psychiatry,
  "Radiology": radiology,
  "Anesthesia": anesthesia
};
