import arcpy
import os
import sys
import datetime, time


def provider_check(provider_name, provider_service_areas):
    sde_db = os.path.dirname(provider_service_areas)
    db_owner_prefix = '.'.join(os.path.basename(provider_service_areas).split('.')[:2])
    providers_tbl = os.path.join(sde_db, f'{db_owner_prefix}.Providers')
    providers = []
    with arcpy.da.SearchCursor(providers_tbl, ['Code']) as scursor:
        for row in scursor:
            providers.append(row[0])

        if provider_name not in providers:
            raise ValueError(f'{provider_name} not found in list of existing providers')
            return arcpy.AddMessage(f'{provider_name} is not an existing broadband provider')

        return provider_name


def edit_version_check(provider_service_areas):

    sde = os.path.dirname(provider_service_areas)

    try:
        describe_gdb = arcpy.Describe(sde)
        connection_props = describe_gdb.connectionProperties
        version = connection_props.version

        if version.endswith('.EDIT') == False:
            raise ValueError(f'{sde} needs to be set to a version named EDIT')
            arcpy.AddMessage(f'{sde} needs to be set to a version named EDIT')
            sys.exit()

    except:
        raise ValueError('Database needs to have a version named EDIT')
        arcpy.AddMessage('Database needs to have a version named EDIT')



def delete_existing_coverage(provider_name, provider_service_areas):
    sde = os.path.dirname(provider_service_areas)
    edit = arcpy.da.Editor(sde)

    provider_name = provider_check(provider_name, provider_service_areas)

    tbl_name = os.path.basename(provider_service_areas)
    if tbl_name.endswith('ProviderServiceAreas') == False:
        raise ValueError('ProviderServiceAreas needs to be the input table')

    deleted = 0

    try:
        edit.startEditing()
        edit.startOperation()

        arcpy.AddMessage(f'Start deleting existing coverage for {provider_name}')
        sql = f'"ProvName" = \'{provider_name}\''
        with arcpy.da.UpdateCursor(provider_service_areas, 'ProvName', sql) as ucursor:
            for row in ucursor:
                ucursor.deleteRow()
                deleted += 1

        edit.stopOperation()
        edit.stopEditing(True)

        arcpy.AddMessage(f'{deleted} {provider_name} records deleted from {tbl_name}')

    except:
        if edit.isEditing:
            edit.stopOperation()
            edit.stopEditing(False)
        arcpy.AddMessage(f'Failed to edit {tbl_name}')


def update_provider_hexagons(provider_name, provider_coverage, provider_service_areas, hexagons):
    sde = os.path.dirname(provider_service_areas)
    edit = arcpy.da.Editor(sde)

    if hexagons[-8:] != 'Hexagons':
        raise ValueError('Hexagons needs to be the input feature class')

    hexagons_fl = arcpy.MakeFeatureLayer_management(hexagons, 'hexagons_fl')
    arcpy.AddMessage(f'Selecting Hexagons that intersect with {provider_coverage}')
    arcpy.SelectLayerByLocation_management(hexagons_fl, 'WITHIN_A_DISTANCE', provider_coverage, '1 METERS')

    selection = arcpy.GetCount_management(hexagons_fl)
    selection_count = int(selection.getOutput(0))

    try:
        edit.startEditing()
        edit.startOperation()

        arcpy.AddMessage(f'{selection_count} hexagons selected')
        arcpy.AddMessage(f'Updating {provider_name} hexagon coverage')

        records_updated = 0

        with arcpy.da.SearchCursor(hexagons_fl, ['HexID']) as scursor, \
            arcpy.da.InsertCursor(provider_service_areas, ['HexID', 'ProvName', 'ServiceClass']) as icursor:

            for row in scursor:
                icursor.insertRow((row[0], provider_name, '1'))

                records_updated += 1
                print(f'Records updated {records_updated}')

        edit.stopOperation()
        edit.stopEditing(True)

        arcpy.AddMessage(f'Added {selection_count} to {provider_name} hexagons')

    except:
        if edit.isEditing:
            edit.stopOperation()
            edit.stopEditing(False)
        arcpy.AddMessage(f'Failed to add {provider_name} hexagons')


if __name__ == '__main__':
    provider_name = arcpy.GetParameterAsText(0)
    provider_coverage = arcpy.GetParameterAsText(1)
    provider_service_areas = arcpy.GetParameterAsText(2)
    hexagons = arcpy.GetParameterAsText(3)

    try:
        provider_name = provider_check(provider_name, provider_service_areas)
        edit_version_check(provider_service_areas)
        delete_existing_coverage(provider_name, provider_service_areas)
        update_provider_hexagons(provider_name, provider_coverage, provider_service_areas, hexagons)

    except arcpy.ExecuteError:
        arcpy.AddError(arcpy.GetMessages(2))
        arcpy.AddMessage('========')
        arcpy.AddMessage(traceback.format_exc())