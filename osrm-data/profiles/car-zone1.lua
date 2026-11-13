-- Profil OSRM Zone 1 : routes goudronnées uniquement
-- Surfaces OSM acceptées : asphalt, paved, concrete
-- Si surface absente : accepte uniquement motorway/trunk/primary/secondary (RN Madagascar)

local base = assert(loadfile('/opt/car.lua'))()

local allowed_surfaces = {
  asphalt = true,
  paved = true,
  concrete = true,
  concrete_lanes = true,
  concrete_plates = true,
  chipseal = true,
}

local trusted_highways_when_no_surface = {
  motorway = true,
  motorway_link = true,
  trunk = true,
  trunk_link = true,
  primary = true,
  primary_link = true,
  secondary = true,
  secondary_link = true,
}

local original_process_way = base.process_way

base.process_way = function(profile, way, result, relations)
  local surface = way:get_value_by_key('surface')
  if surface then
    if not allowed_surfaces[surface] then
      return
    end
  else
    local highway = way:get_value_by_key('highway')
    if not trusted_highways_when_no_surface[highway] then
      return
    end
  end
  return original_process_way(profile, way, result, relations)
end

return base
