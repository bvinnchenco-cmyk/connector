import { Composition } from "remotion";
import { ConcertPromo, ConcertPromoProps } from "./ConcertPromo";

// Default props used in Remotion Studio preview
const defaultProps: ConcertPromoProps = {
  artistName: "Coldplay",
  eventTitle: "Music of the Spheres World Tour",
  date: "20 июля 2025",
  city: "Москва",
  venue: "Лужники",
  siteUrl: "coldplay.tickets.ru",
  imageUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/3/thirty/Coldplay_band_2021.jpg/1280px-Coldplay_band_2021.jpg",
  accentColor: "#00d4ff",
  accentColor2: "#7209b7",
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="ConcertPromo"
      component={ConcertPromo}
      durationInFrames={450}  // 15 seconds at 30fps
      fps={30}
      width={1080}
      height={1080}           // Square for Instagram/Threads
      defaultProps={defaultProps}
    />
  );
};
