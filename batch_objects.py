#!/usr/bin/env python
# -*- coding: utf-8 -*-

import secrets

import csv
import argparse, logging, sys, os
import pprint
pprint = pprint.PrettyPrinter(indent=4).pprint

from pymisp import PyMISP, MISPEvent
from pymisp.tools import GenericObjectGenerator
from pymisp.exceptions import NewAttributeError

log = logging.getLogger('BatchObjects')
LOGGING_FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Upload a CSV of OBJECTS to an EVENT')

    misp_group = parser.add_mutually_exclusive_group(required=True)
    misp_group.add_argument('-e', '--event', metavar='(int|uuid)', type=str, help='EVENT to add the objects to.')
    misp_group.add_argument('-i', '--info', metavar='Badstuff ...', type=str, help="Info field if a new event is to be created")

    parser.add_argument('-d', '--distribution', metavar='[0-4]', type=int, help='Distribution level for object attributes - default is Inherit (level 5) - if distribution is set in CSV that overrides this value')
    parser.add_argument('-c', '--csv', metavar='/path/to/file.csv', nargs='+', required=True, type=str, help='CSV to create the objects from')
    parser.add_argument('--delim', metavar='","', default=',', type=str, help='CSV delimiter')
    parser.add_argument('--quotechar', metavar='"\'"', default='\"', type=str, help='CSV quote character')
    parser.add_argument('--strictcsv', default=True, action='store_false', help='Strict loading of the CSV')
    parser.add_argument('--custom_objects', metavar='/path/to/objects/dir/', dest='custom_objects_path', default=secrets.objects_path, help='If using custom objects provide the path to the objects')
    parser.add_argument('--dryrun', default=False, action='store_true', help='Show objects before sending to MISP')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='Print debug information to stderr')
    args = parser.parse_args()

    if args.verbose or ('DEBUG' in os.environ):
        args.verbose = True # Could have been set by the environment
        pymisp_logger = logging.getLogger('pymisp')
        pymisp_logger.setLevel(logging.DEBUG)
        logging.basicConfig(stream=sys.stderr, format=LOGGING_FORMAT, level=logging.DEBUG)
    else:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logging.basicConfig(stream=sys.stderr, format=LOGGING_FORMAT, level=logging.INFO)


    pymisp = PyMISP(secrets.misp_url, secrets.misp_key, secrets.misp_validate_cert, debug=args.verbose)

    template = pymisp.get_object_templates_list()
    if 'response' in template.keys():
        template = template['response']
    else:
        log.critical('Could not get templates')
        exit(1)

    objects = []
    for csvfile in args.csv:
        objects_file = csv.DictReader(
            open(csvfile),
            delimiter=args.delim,
            quotechar=args.quotechar,
            strict=args.strictcsv
        )

        for row in objects_file:
            obj = {
                'data': []
            }
            for field, value in row.items():
                if field == 'object':
                    obj['object'] = value.lower()
                elif field == 'distribution':
                    obj['distribution'] = value
                elif field == 'comment':
                    obj['comment'] = value
                elif value:
                    field = str(field.split('__')[0].lower())
                    obj['data'].append({field:value})

            objects.append(obj)

    if args.info:
        event = MISPEvent()
        event.info = args.info
        if args.distribution:
            event.distribution = args.distribution

        if not args.dryrun:

            new_event = pymisp.add_event(event)

            if 'errors' in new_event.keys():
                log.critical('Error creating the new event. Error: {}'.format('; '.join(new_event['errors'])))
                exit(1)

            args.event = new_event['Event']['uuid']
            log.info('New event created: {}'.format(args.event))

    for o in objects:
        misp_object = GenericObjectGenerator(o['object'],  misp_objects_path_custom=args.custom_objects_path)
        try:
            misp_object.generate_attributes(o['data'])
        except NewAttributeError as e:
            log.critical('Error creating attributes, often this is due to custom objects being used. Error: {}'.format(e))
            exit(1)

        # # Add distribution if it has been set
        if o.get('distribution'):
            misp_object.distribution = o.get('distribution')
        elif args.distribution:
            misp_object.distribution = args.distribution

        # # Add comment to object if it has been set
        if o['comment']:
            misp_object.comment = o['comment']

        # # Just print the object if --dryrun has been used
        log.info('Processing object: {}'.format(misp_object.to_json()))
        if args.dryrun:
            continue
        else:

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
