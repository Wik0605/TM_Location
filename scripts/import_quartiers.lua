local quartiers = osm2pgsql.define_table({
    name = 'quartiers',
    ids = { type = 'relation', id_column = 'osm_id' },
    columns = {
        { column = 'nom',       type = 'text' },
        { column = 'nom_court', type = 'text' },
        { column = 'type',      type = 'text' },
        { column = 'actif',     type = 'boolean' },
        { column = 'geom',      type = 'geometry', projection = 4326 },
    },
    create = false,
})

function osm2pgsql.process_relation(object)
    local level = object.tags['admin_level']
    if level ~= '8' and level ~= '10' then
        return
    end

    local nom = object.tags['name'] or ''
    if nom == '' then return end

    quartiers:insert({
        nom       = nom,
        nom_court = object.tags['short_name'] or nom,
        type      = level == '10' and 'fokontany' or 'commune',
        actif     = true,
        geom      = object:as_multipolygon(),
    })
end
