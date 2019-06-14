#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import argparse, logging, sys, os, configparser
import pprint

pprint = pprint.PrettyPrinter(indent=4).pprint
script_path = os.path.dirname(os.path.realpath(__file__))

log = logging.getLogger('BatchObjects')
LOGGING_FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'

config = configparser.ConfigParser(inline_comment_prefixes=(';',))
config_path = '{}/config.ini'.format(script_path)
try:
    config.read(config_path)
except Exception as e:
    print('Error loading {}, copy the config.ini.sample: {}'.format(config_path, e))
    exit(1)
config.BOOLEAN_STATES = {'yes': True, 'no': False}

from pymisp import PyMISP, MISPEvent
from pymisp.tools import GenericObjectGenerator
from pymisp.exceptions import NewAttributeError

def get_object_meta(object_name, field):
    try:
        object_meta = config['OBJECT_META']
    except:
        log.warning('No OBJECT_META section found in config.ini - using MISP defaults')
        return {}

    user_defs = {}

    for key in object_meta.keys():
        o_object_name, o_field, o_option = key.split('.')

        if o_object_name != object_name or o_field != field:
            continue

        try: value = object_meta.getboolean(key)
        except:
            try: value = object_meta.getint(key)
            except:
                try: value = object_meta.getfloat(key)
                except:
                    value = object_meta.get(key)

        user_defs[o_option] = value

    return(user_defs)

def get_object_fields(csv_path, delim, quotechar, strictcsv):

    objects = []
    for csvfile in csv_path:
        objects_file = csv.DictReader(
            open(os.path.abspath(csvfile)),
            delimiter=delim,
            quotechar=quotechar,
            strict=strictcsv
        )

        for i, row in enumerate(objects_file, 1): # Start from 1 as header is consumed by DictReader already
            # # Ignore lines with comments, as their own column (as per the templates), or prefixed to object column
            if row['object'] == '':
                log.debug('Ignoring row "{}", no object given!'.format(i))
                continue
            elif row['object'].strip().startswith('#'):
                log.debug('Ignoring row "{}", commented out!'.format(i))
                continue
            try:
                if row['#'].strip().startswith('#'):
                    log.debug('Ignoring row "{}", commented out!'.format(i))
                    continue
            except: pass
            try:
                if row[''].strip().startswith('#'):
                    log.debug('Ignoring row "{}", commented out!'.format(i))
                    continue
            except: pass

            raw_obj = {
                'object': None,
                'attributes': []
            }
     
            
            # # Mandatory Object name field!
            try:
                raw_obj['object'] = row.pop('object').lower().strip()
            except Exception as e:
                log.critical('No "object" column defined in CSV!' + str(e))
                exit(1)
            # # Distribution should always be a number
            try: raw_obj['object_distribution'] = int(row.pop('object_distribution').strip())
            except: pass
            # # Get object comment
            try: raw_obj['object_comment'] = int(row.pop('object_comment').strip())
            except: pass

            for field, value in row.items():
                field, value = field.strip(), value.strip()

                # # Ignore templates which use "-", or blank fields
                if value == '-' or field == '' or value == '': # # Sometimes people leave blank columns... AH
                    continue
                # # Other object fields
                elif value:
                    field_str = str(field.split('__')[0].lower()) # Allow for duplicate field names
                    field_meta = get_object_meta(raw_obj['object'] , field_str)
                    field_data = { **{'value':value}, **field_meta}
                    raw_obj['attributes'].append({field_str: field_data})

            objects.append(raw_obj)

    return objects

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Upload a CSV of OBJECTS to an EVENT')

    # # MISP options
    parser.add_argument('--misp_url', dest='misp_url', metavar='"http://misp.local"', default=config['MISP'].get('url'), help='MISP URL (overrides conf.ini)')
    parser.add_argument('--misp_key', dest='misp_key', metavar='<API_KEY>', default=config['MISP'].get('key'), help='MISP API key (overrides conf.ini)')
    parser.add_argument('--misp_validate_cert', dest='misp_validate_cert', action='store_true', default=config['MISP'].getboolean('validate_cert'), help='Validate MISP SSL certificate (overrides conf.ini)')
    parser.add_argument('--custom_objects', metavar='/path/to/objects/dir/', dest='custom_objects_path', default=config['MISP'].get('custom_objects_path'), help='If using custom objects, provide the path to the object json (overrides conf.ini)')

    # # CSV options
    parser.add_argument('--delim', metavar='","', default=config['CSV_READER'].get('delimiter'), type=str, help='CSV delimiter')
    parser.add_argument('--quotechar', metavar='"\'"', default=config['CSV_READER'].get('quote_character'), type=str, help='CSV quote character')
    parser.add_argument('--strictcsv', default=config['CSV_READER'].getboolean('strict_csv_parsing'), action='store_false', help='Strict loading of the CSV')
    parser.add_argument('--dryrun', default=False, action='store_true', help='Show objects before sending to MISP')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='Print debug information to stderr')

    # # Event creation options
    misp_group = parser.add_mutually_exclusive_group(required=True)
    misp_group.add_argument('-e', '--event', metavar='(int|uuid)', type=str, help='EVENT to add the objects to.')
    misp_group.add_argument('-i', '--info', metavar='"Title for new event" ...', type=str, help="Info field if a new event is to be created")
    parser.add_argument('--dist', '--distribution', dest='distribution', metavar='[0-4]', default=config['MISP'].getint('default_distribution'), type=int, help='Event distribution level - New events ONLY (--info) (overrides conf.ini)')

    # # CSV to parse option
    parser.add_argument('-c', '--csv', metavar='/path/to/file.csv', nargs='+', required=True, type=str, help='CSV to create the objects from')
    args = parser.parse_args()

    # # Args tests
    if args.verbose or ('DEBUG' in os.environ):
        args.verbose = True # Could have been set by the environment
        pymisp_logger = logging.getLogger('pymisp')
        pymisp_logger.setLevel(logging.DEBUG)
        logging.basicConfig(stream=sys.stderr, format=LOGGING_FORMAT, level=logging.DEBUG)
    else:
        # # urllib3 is noisy
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logging.basicConfig(stream=sys.stderr, format=LOGGING_FORMAT, level=logging.INFO)

    # # Connect to MISP
    pymisp = PyMISP(args.misp_url, args.misp_key, args.misp_validate_cert, debug=args.verbose)

    # # Get current object templates
    template = pymisp.get_object_templates_list()
    if 'response' in template.keys():
        template = template['response']
    else:
        log.critical('Could not get templates from MISP!')
        exit(1)

    # # Load objects from the CSV file
    objects = get_object_fields(args.csv, args.delim, args.quotechar, args.strictcsv)
    if len(objects) == 0:
        log.critical('No Objects to create! Are they commented out? Run with --verbose (-v) to see what\'s happening!')
        exit(1)

    # # Create a new Event
    if args.info:
        event = MISPEvent()
        event.info = args.info
        if args.distribution:
            log.debug('Setting distribution level for Event: {}'.format(args.distribution))
            event.distribution = args.distribution

        if not args.dryrun:
            new_event = pymisp.add_event(event)

            if 'errors' in new_event.keys():
                log.critical('Error creating the new event. {}'.format(new_event['errors'][2]))
                exit(1)

            # # Get the ID of the new event for later
            args.event = new_event['Event']['uuid']
            log.info('New event created: {}'.format(args.event))

    # # Add Objects to existing Event
    for i, o in enumerate(objects, 1):
        misp_object = GenericObjectGenerator(o['object'],  misp_objects_path_custom=args.custom_objects_path)
        try:
            misp_object.generate_attributes(o['attributes'])
        except NewAttributeError as e:
            log.critical('Error creating attributes, often this is due to custom objects being used. Error: {}'.format(e))
            exit(1)

        # # Add distribution if it has been set
        try: misp_object.distribution = o.get('object_distribution')
        except: pass
        # # Add comment to object if it has been set
        try: misp_object.comment = o.get('object_comment')
        except: pass

        # # Just print the object if --dryrun has been used
        if args.dryrun:
            log.info('Adding object ({}): {}'.format(o['object'], misp_object.to_json()))
            continue
        else:

            if not log.level == logging.DEBUG:
                log.info('Adding object {} - {}'.format(i, o['object']))
            else:
                log.info('Adding object ({}): {}'.format(o['object'], misp_object.to_json()))

            try:
                template_ids = [x['ObjectTemplate']['id'] for x in template if x['ObjectTemplate']['name'] == o['object']]
                if len(template_ids) > 0:
                    template_id = template_ids[0]
                else:
                    raise IndexError
            except IndexError:
                valid_types = ", ".join([x['ObjectTemplate']['name'] for x in template])
                log.critical("Template for type %s not found! Valid types are: %s" % (args.type, valid_types))
                exit(1)

            response = pymisp.add_object(args.event, template_id, misp_object)

            if 'errors' in response.keys():
                log.critical('Error in MISP response! Exiting!')
                log.critical(response['errors'])
                exit(1)

    if not args.dryrun:
        log.info('Event: {}/events/view/{}'.format(args.misp_url, args.event))