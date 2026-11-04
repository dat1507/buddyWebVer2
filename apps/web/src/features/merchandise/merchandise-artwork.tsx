import { Shirt, ShoppingBag } from 'lucide-react'
/** Existing decorative concept artwork shared with the Coming Soon page. */
export function MerchandiseArtwork() {
  return (
    <div className="merchandise-art" aria-hidden="true">
      <div className="merchandise-orbit" />
      <div className="merchandise-shirt">
        <Shirt strokeWidth={1.15} />
        <span>BUDDY</span>
      </div>
      <div className="merchandise-bag">
        <ShoppingBag strokeWidth={1.15} />
        <span>
          VGU
          <br />
          BUDDY
        </span>
      </div>
      <span className="merchandise-star">✦</span>
      <span className="merchandise-art-note">MEET · CONNECT · BELONG</span>
    </div>
  )
}
