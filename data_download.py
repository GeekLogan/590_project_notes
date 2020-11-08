import pandas as pd
import urllib
import xmltodict

from multiprocessing import Pool

POOL_SIZE = 50

def do_request( url ):
    file = urllib.request.urlopen( url )
    data = file.read()
    file.close()
    data = xmltodict.parse(data)
    return data

def get_all_samples():
    return do_request( 'http://api.brain-map.org/api/v2/data/query.xml?criteria=model::Specimen,rma::criteria,products[name$eq%27Glioblastoma%27],rma::options[num_rows$eqall]' )

all_samples_resp = get_all_samples()
all_specimens = sorted( [ x['external-specimen-name'] for x in all_samples_resp['Response']['specimens']['specimen'] ] )
print( 'Found {} samples'.format( len(all_specimens) ) )

def get_sample_detail( specimen='W1-1-2-A.1.01' ):
    return do_request( "http://api.brain-map.org/api/v2/data/query.xml?criteria=model::SectionDataSet,rma::criteria,specimen[external_specimen_name$eq'{}'],rma::include,genes,sub_images".format(specimen) )

def get_all_section_images( specimen='W1-1-2-A.1.01' ):
    data = get_sample_detail( specimen )
    
    out = []
    try:
        data = data['Response']['section-data-sets']['section-data-set']
    except:
        return out
    
    if type(data) != list:
        data = [data]
    
    for a in data:
        if not 'genes' in a:
            continue
        if a['genes'] is not None:
            try:
                out.append(
                    (
                        a['genes']['gene']['acronym'],
                        a['sub-images']['sub-image']['id']['#text'],
                        a['sub-images']['sub-image']['section-number']['#text']
                    )
                )
            except:
                pass
        else:
            for i,sub_image in enumerate( a['sub-images']['sub-image'] ):
                try:
                    out.append( ('H+E', sub_image['id']['#text'], sub_image['section-number']['#text']) )
                except:
                    pass
                
    for i,a in enumerate(out):
        a = out[i]
        out[i] = ( a[0], int(a[1]), int(a[2]) )
        
    return sorted( out, key=lambda x: x[2] )

def download_image_from_id( id_str, name=None, feature_map=False ):
    if not name:
        name = id_str
        
    url = "http://api.brain-map.org/api/v2/image_download/{}".format(id_str)
    if feature_map:
        url += '?view=tumor_feature_annotation'
        
    urllib.request.urlretrieve(url, "{}.jpg".format(name))

def download_unpack( x ):
    download_image_from_id( x[0], name=x[1], feature_map=x[2] )
    return 0

for specimen in all_specimens:
    print( "Starting specimen", specimen, "...")
    
    to_download = []
    images = get_all_section_images( specimen )
    
    for gene,image,slice_num in images:
        name = './data_tmp/'
        name += specimen + '.GENE_' + gene + '.SLICE_' + str(slice_num)
        
        to_download.append( ( image, name, False ) )
        name += '.MAP'
        to_download.append( ( image, name, True ) )
        
    with Pool( POOL_SIZE ) as p:
        p.map( download_unpack, to_download )