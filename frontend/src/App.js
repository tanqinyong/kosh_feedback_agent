import React, { useState } from "react";

function App() {
  const [input, setInput] = useState("");
  const [chatLog, setChatLog] = useState([{
    user: "gpt",
    message: "Welcome to Kosh Feedback Agent! Upload your report and I'll give you some feedback."
  }, 
  ]);

  function clearChat() {
    setChatLog([{
      user: "gpt",
      message: "Welcome to Kosh Feedback Agent! Upload your report and I'll give you some feedback."
    }]);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setChatLog(chatLog => [...chatLog, { user: "Me", message: `${input}`} ]);
    setInput("");

    // Fetch response from API
    const response = await fetch("http://www.localhost:8000/api/query_chatgpt/", {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        // Entire chat history
        message: chatLog.map((message) => message.message).join("\n") + "\n\n" + "Latest user query (to answer): " + input
      })
    });

    const data = await response.json();
    setChatLog(chatLog => [...chatLog, { user: "gpt", message: `${data.response}`} ]);
  }

  const ChatMessageGPT = ({ message }) => {
    return (
      <div className="bg-gray-600">
        <div className="flex w-full p-2 gap-3 mx-auto px-4">
          <div className="w-8 h-8 rounded-xl bg-white flex-shrink-0">
            <img src="/kosh.png" alt="AI Avatar" className="w-full h-full rounded-xl" />
          </div>
          <div className="message">
            {message.message}
          </div>
        </div>
      </div>
    );
  };  

  const ChatMessageUser = ({ message }) => {
    return (
      <div className="">
        <div className="flex w-full p-2 gap-3 mx-auto px-4">
          <div className="w-8 h-8 rounded-xl bg-white flex-shrink-0">
            <img src="https://i.pravatar.cc/150?img=31" alt="Human Avatar" className="w-full h-full rounded-xl" />
          </div>
          <div className="message">
            {message.message}
          </div>
        </div>
      </div>
    );
  };  

  return (
    <div className="flex text-center text-white w-screen h-screen bg-gray-700">

      {/* Sidebar */}
      <aside className="w-1/5 p-2 border bg-gray-800 border-gray-700 ">
        <div className="flex p-2 items-center gap-2 border rounded-sm border-white hover:bg-white hover:bg-opacity-10 transition-all duration-300"
             onClick={clearChat}>
          <span>+</span>
          New Chat
        </div>
      </aside>

      {/* Chat Area */}
      <section className="flex-1 w-3/4 relative border border-gray-700 ">
        
        {/* Chat Log */}
        <div className="text-left h-full overflow-y-auto pb-20">
          {chatLog.map((message, index) => {
            return message.user === "gpt" ? <ChatMessageGPT key={index} message={message} /> 
                                          : <ChatMessageUser key={index} message={message} />
          })}
        </div>

        {/* Chat Input */}
        <div className="flex flex-row w-4/5 absolute bottom-3 left-1/2 transform -translate-x-1/2">
          <form onSubmit={handleSubmit} className="flex flex-row w-full">
            <input className="flex-1 p-2 m-1 border border-none rounded-md bg-gray-600 outline-none shadow-lg " 
                   value={input}
                   onChange={(e) => setInput(e.target.value)}
                   placeholder="Ask Kosh Agent for some feedback!"></input>
            <button onClick={handleSubmit} className="flex-none p-2 m-1 rounded-md bg-gray-800 text-white ">↵</button>
          </form>
        </div>

      </section>
    </div>
  );

}

export default App;
