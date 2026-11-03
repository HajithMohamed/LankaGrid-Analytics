export function Footer() {
  return (
    <footer className="w-full border-t border-[#E7EBF0] bg-white py-8 mt-16 text-[12px] text-[#9AA5B0]">
      <div className="max-w-[1500px] mx-auto px-4 md:px-9 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <span className="font-semibold text-[#637185]">GridLens Analytics</span>
          <span className="mx-2 text-[#CBD5E1]">·</span>
          <span>Sri Lanka National Electricity Grid Data Warehouse</span>
        </div>

        <div className="text-center md:text-left">
          <span>Department of Information &amp; Communication Technology</span>
          <span className="mx-2 text-[#CBD5E1]">·</span>
          <span>Faculty of Technology, University of Ruhuna</span>
        </div>

        <div>
          <span className="font-semibold text-[#637185]">Sources:</span>{" "}
          <span>PUCSL · CEB · NASA POWER (2020–2024)</span>
        </div>
      </div>
    </footer>
  );
}
