// Copied from https://www.bls.gov/cew/cewedr10.htm
var fips_postalcode = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "72": "PR", "78": "VI"
    };

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

function get_autocomplete(state_id)
{
    var indexed = index_geographies(us_states, us_counties);
    indexed.suggestion_fips = {};

    function on_source(request, response)
    {
        var term_query = request.term.trim().toLowerCase(),
            term_parts = term_query.split(/\s+/),
            term_matches = [];
    
        console.log('term_parts:', term_parts);
    
        // create a list of lists, one for each part of the search term
        for(var i in term_parts)
        {
            var part_matches = indexed.index[term_parts[i]];
            term_matches.push(part_matches);
        }

        // calculate intersection of all those lists to match all terms
        var matched_fips = intersect_lists(term_matches).sort();
    
        // build up a list of suggestions
        var seen_fips = {}, suggestions1 = [], suggestions2 = [];
        indexed.suggestion_fips = {};
    
        for(var i in matched_fips)
        {
            var fips = matched_fips[i],
                full_name = indexed.fullnames[fips],
                short_name = indexed.names[fips];

            if(fips in seen_fips) {
                // skip any non-new suggestions
                continue;
            } else {
                seen_fips[fips] = true;
            }

            // add new suggestions to the lists
            if(full_name.toLowerCase().substr(0, term_query.length) == term_query) {
                // complete prefix matches go to the first list
                suggestions1.push({label: full_name, value: short_name});
            } else {
                // other matches go to the second list
                suggestions2.push({label: full_name, value: short_name});
            }
        
            indexed.suggestion_fips[full_name] = fips;
        }
        
        // return just the first few to keep the UI snappy
        response(suggestions1.concat(suggestions2).slice(0, 10));
    }
    
    function on_select(event, ui)
    {
        var state_select = document.getElementById(state_id),
            selected_fips = indexed.suggestion_fips[ui.item.label],
            state_code = fips_postalcode[selected_fips.substr(0, 2)];
        
        console.log('changed', ui.item.label, selected_fips, state_code);
        
        for(var i in state_select.options)
        {
            state_select.options[i].selected = (state_select.options[i].value == state_code);
        }
    }
    
    return {
        source: on_source,
        select: on_select
        };
}
