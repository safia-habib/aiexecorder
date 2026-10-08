import { ComposableMap, Geographies, Geography } from 'react-simple-maps'

// us-atlas v3 — FIPS-based TopoJSON with properties.name = state name
const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json'

const NAME_TO_CODE = {
  Alabama: 'AL', Alaska: 'AK', Arizona: 'AZ', Arkansas: 'AR',
  California: 'CA', Colorado: 'CO', Connecticut: 'CT', Delaware: 'DE',
  Florida: 'FL', Georgia: 'GA', Hawaii: 'HI', Idaho: 'ID',
  Illinois: 'IL', Indiana: 'IN', Iowa: 'IA', Kansas: 'KS',
  Kentucky: 'KY', Louisiana: 'LA', Maine: 'ME', Maryland: 'MD',
  Massachusetts: 'MA', Michigan: 'MI', Minnesota: 'MN', Mississippi: 'MS',
  Missouri: 'MO', Montana: 'MT', Nebraska: 'NE', Nevada: 'NV',
  'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
  'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND',
  Ohio: 'OH', Oklahoma: 'OK', Oregon: 'OR', Pennsylvania: 'PA',
  'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD',
  Tennessee: 'TN', Texas: 'TX', Utah: 'UT', Vermont: 'VT',
  Virginia: 'VA', Washington: 'WA', 'West Virginia': 'WV',
  Wisconsin: 'WI', Wyoming: 'WY',
}

const FILL_HAS_EO       = '#2980b9'
const FILL_HAS_EO_HOVER = '#1f618d'
const FILL_SELECTED     = '#154360'
const FILL_NO_EO        = '#d5d8dc'
const FILL_NO_EO_HOVER  = '#bfc4c9'

export default function StateMap({ stateMap, selectedCode, onSelect }) {
  return (
    <ComposableMap
      projection="geoAlbersUsa"
      style={{ width: '100%', height: 'auto' }}
    >
      <Geographies geography={GEO_URL}>
        {({ geographies }) =>
          geographies.map(geo => {
            const name = geo.properties.name
            const code = NAME_TO_CODE[name]
            const hasEo = Boolean(code && stateMap[code]?.has_eo)
            const isSelected = code === selectedCode

            const fill = isSelected
              ? FILL_SELECTED
              : hasEo ? FILL_HAS_EO : FILL_NO_EO

            const hoverFill = isSelected
              ? FILL_SELECTED
              : hasEo ? FILL_HAS_EO_HOVER : FILL_NO_EO_HOVER

            return (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                onClick={() => code && onSelect(code)}
                title={
                  hasEo
                    ? `${name} — click to view EO`
                    : `${name} — no AI executive order on file`
                }
                tabIndex={hasEo ? 0 : -1}
                onKeyDown={e => {
                  if ((e.key === 'Enter' || e.key === ' ') && code) onSelect(code)
                }}
                style={{
                  default: {
                    fill,
                    stroke: '#ffffff',
                    strokeWidth: 0.5,
                    outline: 'none',
                    cursor: hasEo ? 'pointer' : 'default',
                  },
                  hover: {
                    fill: hoverFill,
                    stroke: '#ffffff',
                    strokeWidth: 0.5,
                    outline: 'none',
                    cursor: hasEo ? 'pointer' : 'default',
                  },
                  pressed: {
                    fill: FILL_SELECTED,
                    stroke: '#ffffff',
                    strokeWidth: 0.5,
                    outline: 'none',
                  },
                }}
              />
            )
          })
        }
      </Geographies>
    </ComposableMap>
  )
}
