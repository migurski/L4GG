/**
 * Create an inverted index of U.S. county and state names.
 */
function index_geographies(us_states, us_counties)
{
    var start_time = (new Date()).getTime(),
        state_names = {}, // state names: "California"
        county_names = {}, // local county names: "Yolo County"
        county_fullnames = {}, // full county names: "Yolo County, California"
        name_index = {}; // name token index to arrays of FIPS codes

    for(var i = 1; i < us_states.length; i++)
    {
        var fips = us_states[i][1], name = us_states[i][0];
        state_names[fips] = name;
    }
    
    for(var i = 1; i < us_counties.length; i++)
    {
        var state_fips = us_counties[i][1],
            fips = state_fips + us_counties[i][2],
            name = us_counties[i][0],
            state_name = state_names[state_fips],
            name_parts = (name + ' ' + state_name).toLowerCase().split(/\s+/);

        county_names[fips] = name;
        county_fullnames[fips] = name + ', ' + state_name;
        
        for(var j in name_parts)
        {
            // index every variant of a name
            for(var k = 1; k <= name_parts[j].length; k++)
            {
                var name_part = name_parts[j].substr(0, k);
            
                if(name_part in name_index) {
                    name_index[name_part].push(fips);
            
                } else {
                    name_index[name_part] = [fips];
                }
            }
        }
    }
    
    var index_time = (new Date()).getTime() - start_time;
    console.log(['Indexed counties in', index_time, 'msec'].join(' '));
    return {index: name_index, names: county_names, fullnames: county_fullnames};
}

/**
 * Find intersection of a list of lists and return it.
 */
function intersect_lists(inputs)
{
    // slice(0) copies the array
    var output = inputs[0].slice(0);
    
    for(var i = 1; i < inputs.length; i++)
    {
        for(var j = output.length - 1; j >= 0; j--)
        {
            // remove output elements not present in any of the other lists
            if(inputs[i].indexOf(output[j]) == -1)
            {
                output.splice(j, 1);
            }
        }
    }
    
    return output;
}
