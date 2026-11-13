-- Profil OSRM Zone 3 : toutes routes (tout-terrain)
-- Pas de filtre sur surface, bloque uniquement les ways manifestement impraticables en voiture
-- (sentiers piétons, pistes cyclables, etc. déjà filtrés par le profil car standard)

local base = assert(loadfile('/opt/car.lua'))()

local blocked_surfaces = {
  mud = true,
}

local original_process_way = base.process_way

base.process_way = function(profile, way, result, relations)
  local surface = way:get_value_by_key('surface')
  if surface and blocked_surfaces[surface] then
    return
  end
  return original_process_way(profile, way, result, relations)
end

return base
