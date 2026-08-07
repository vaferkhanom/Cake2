declare module "suncalc3" {
  interface SunPosition {
    azimuth: number; // radians, 0 = south
    altitude: number; // radians, 0 = horizon
    altitudeRounded: number;
    azimuthRounded: number;
  }

  interface SunTimes {
    sunrise: Date | null;
    sunset: Date | null;
    dawn: Date | null;
    dusk: Date | null;
    goldenHourEnd: Date | null;
    goldenHour: Date | null;
    [key: string]: Date | null;
  }

  interface MoonPosition {
    azimuth: number;
    altitude: number;
    distance: number;
    parallacticAngle: number;
  }

  interface MoonIllumination {
    fraction: number; // 0 to 1
    phase: { from: number; to: number; id: string; emoji: string; name: string; weight: number; css: string; }; // phase info object
    phaseValue: number; // 0 to 1 (0=new, 0.5=full) — use this for sprite selection
    angle: number;
  }

  function getPosition(date: Date, lat: number, lng: number): SunPosition;
  function getTimes(date: Date, lat: number, lng: number): SunTimes;
  function getMoonPosition(date: Date, lat: number, lng: number): MoonPosition;
  function getMoonIllumination(date: Date): MoonIllumination;
}
