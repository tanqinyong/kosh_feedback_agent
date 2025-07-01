

function App() {
  return (
    <div className="flex text-center text-white w-screen h-screen bg-gray-700">

      {/* Sidebar */}
      <aside className="w-1/5 p-2 border bg-gray-800 border-gray-700 ">
        <div className="flex p-2 items-center gap-2 border rounded-sm border-white hover:bg-white hover:bg-opacity-10 transition-all duration-300">
          <span>+</span>
          New Chat
        </div>
      </aside>

      {/* Chat Area */}
      <section className="flex-1 w-3/4 relative border border-gray-700">
        
        {/* Chat Log */}
        <div className="text-left">
          {/* Chat Message - AI */}
          <div className=" bg-gray-600">
            <div className="flex w-full p-2 gap-3 mx-auto px-4">
              <div className="w-8 h-8 rounded-xl bg-white">
                <img src="/kosh.png" alt="AI Avatar" className="w-full h-full rounded-xl" />
              </div>
              <div className="">
                The summary of your report is as follows:
              </div>
            </div>
          </div>

          {/* Chat Message - Human */}
          <div className="">
            <div className="flex w-full p-2 gap-3 mx-auto px-4">
              <div className="w-8 h-8 rounded-xl bg-white">
                <img src="https://i.pravatar.cc/150?img=31" alt="Human Avatar" className="w-full h-full rounded-xl" />
              </div>
              <div className="">
                Wow ok so what next?
              </div>
            </div>
          </div>
        </div>

        {/* Chat Input */}
        <div className="flex flex-row w-4/5 absolute bottom-3 left-1/2 transform -translate-x-1/2">
          <textarea className="flex-1 p-2 m-1 border border-none rounded-md bg-gray-600 outline-none shadow-lg " 
                    placeholder="Ask Kosh Agent for some feedback!"></textarea>
          <button className="flex-none p-2 m-1 rounded-md bg-gray-800 text-white ">↵</button>
        </div>

      </section>
    </div>
  );
}

export default App;
