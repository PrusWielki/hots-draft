<script>
  import { onMount } from "svelte";

  // Maps listing
  const MAPS = [
    { id: "alterac_pass", name: "Alterac Pass" },
    { id: "battlefield_of_eternity", name: "Battlefield of Eternity" },
    { id: "braxis_holdout", name: "Braxis Holdout" },
    { id: "cursed_hollow", name: "Cursed Hollow" },
    { id: "dragon_shire", name: "Dragon Shire" },
    { id: "garden_of_terror", name: "Garden of Terror" },
    { id: "hanamura_temple", name: "Hanamura Temple" },
    { id: "infernal_shrines", name: "Infernal Shrines" },
    { id: "sky_temple", name: "Sky Temple" },
    { id: "tomb_of_the_spider_queen", name: "Tomb of the Spider Queen" },
    { id: "towers_of_doom", name: "Towers of Doom" },
    { id: "volskaya_foundry", name: "Volskaya Foundry" }
  ];

  // Svelte 5 Runes for State management
  let heroes = $state([]);
  let draftState = $state({
    map_name: "",
    my_team_picks: [],
    my_team_bans: [],
    enemy_picks: [],
    enemy_bans: [],
    my_team_first: true,
    is_complete: false,
    current_step: null
  });
  let recommendations = $state([]);
  let banRecommendations = $state([]);
  let activeRecTab = $state("picks");
  let searchQuery = $state("");
  let selectedRole = $state("All");
  let selectedTag = $state("All");

  // Hero Details / Inspector state
  let inspectedHeroId = $state("johanna");
  let inspectedHero = $derived(heroes.find(h => h.id === inspectedHeroId) || null);
  let selectedBuildIdx = $state(0);

  $effect(() => {
    // Reset build index when inspected hero changes
    if (inspectedHeroId) {
      selectedBuildIdx = 0;
    }
  });

  $effect(() => {
    if (draftState.current_step) {
      if (draftState.current_step.action === "ban") {
        activeRecTab = "bans";
      } else {
        activeRecTab = "picks";
      }
    }
  });
  
  // Connection state
  let socket = null;
  let wsStatus = $state("connecting");
  let backendUrl = $state("");

  // Determine backend and websocket locations
  onMount(async () => {
    const host = window.location.hostname;
    const httpPort = "8000";
    backendUrl = `http://${host}:${httpPort}`;
    
    // Fetch all heroes metadata
    await fetchHeroes();

    // Initialize websocket connection
    connectWebSocket(host, httpPort);

    return () => {
      if (socket) socket.close();
    };
  });

  async function fetchHeroes() {
    try {
      const res = await fetch(`${backendUrl}/api/heroes`);
      if (res.ok) {
        heroes = await res.json();
      }
    } catch (e) {
      console.error("Failed to fetch heroes: ", e);
    }
  }

  function connectWebSocket(host, port) {
    wsStatus = "connecting";
    socket = new WebSocket(`ws://${host}:${port}/ws/draft`);

    socket.onopen = () => {
      wsStatus = "connected";
      console.log("WebSocket connected.");
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.draft_state) {
          draftState = payload.draft_state;
        }
        if (payload.recommendations) {
          recommendations = payload.recommendations;
        }
        if (payload.ban_recommendations) {
          banRecommendations = payload.ban_recommendations;
        }
      } catch (e) {
        console.error("Error parsing WS message:", e);
      }
    };

    socket.onclose = () => {
      wsStatus = "disconnected";
      console.log("WebSocket disconnected. Retrying in 2 seconds...");
      setTimeout(() => connectWebSocket(host, port), 2000);
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
      socket.close();
    };
  }

  // Trigger state transitions via HTTP/WS
  function sendEvent(eventType, details = {}) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error("WebSocket not ready.");
      return;
    }
    const payload = { event_type: eventType, ...details };
    socket.send(JSON.stringify(payload));
  }

  function selectHero(heroId) {
    if (draftState.is_complete) return;
    
    const step = draftState.current_step;
    if (!step) return;

    sendEvent(step.action, { hero_id: heroId });
  }

  function handleMapChange(e) {
    sendEvent("map_select", { map_name: e.target.value });
  }

  function toggleFirstPick() {
    sendEvent("set_first_pick", { my_team_first: !draftState.my_team_first });
  }

  function resetDraft() {
    sendEvent("reset");
  }

  async function reloadDB() {
    try {
      const res = await fetch(`${backendUrl}/api/db/reload`, { method: "POST" });
      if (res.ok) {
        await fetchHeroes();
        alert("Heroes database reloaded successfully!");
      }
    } catch (e) {
      alert("Failed to reload DB: " + e.message);
    }
  }

  function undoLast() {
    sendEvent("undo");
  }

  // Derived filter calculations (Svelte 5 Runes)
  let allTags = $derived.by(() => {
    const tags = new Set();
    heroes.forEach(h => h.tags.forEach(t => tags.add(t)));
    return ["All", ...Array.from(tags).sort()];
  });

  let filteredHeroes = $derived.by(() => {
    // Filter out already drafted heroes
    const drafted = new Set([
      ...draftState.my_team_picks,
      ...draftState.my_team_bans,
      ...draftState.enemy_picks,
      ...draftState.enemy_bans
    ]);

    return heroes.filter(hero => {
      if (drafted.has(hero.id)) return false;
      
      const matchesSearch = hero.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            hero.id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesRole = selectedRole === "All" || hero.role === selectedRole;
      const matchesTag = selectedTag === "All" || hero.tags.includes(selectedTag);

      return matchesSearch && matchesRole && matchesTag;
    }).sort((a, b) => a.name.localeCompare(b.name));
  });

  // Helpers to fetch full hero object
  function getHero(id) {
    return heroes.find(h => h.id === id) || { id, name: id, role: "Unknown" };
  }

  function getRoleAbbreviation(role) {
    switch (role) {
      case "Tank": return "T";
      case "Bruiser": return "B";
      case "Healer": return "H";
      case "Melee Assassin": return "MA";
      case "Ranged Assassin": return "RA";
      case "Support": return "S";
      default: return "?";
    }
  }
</script>

<main class="min-h-screen p-6 flex flex-col gap-6">
  <!-- Top Bar Controls -->
  <header class="glass-panel p-4 flex flex-wrap items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <div class="h-10 w-10 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center font-bold text-xl shadow-lg border border-purple-500/30">
        Ω
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight text-white font-outfit">NexusDraft</h1>
        <div class="flex items-center gap-2 text-xs">
          <span class="h-2 w-2 rounded-full {wsStatus === 'connected' ? 'bg-emerald-500' : wsStatus === 'connecting' ? 'bg-amber-500' : 'bg-rose-500'}"></span>
          <span class="text-gray-400 capitalize">{wsStatus === "connected" ? "Live Stream" : wsStatus}</span>
        </div>
      </div>
    </div>

    <!-- Configuration Options -->
    <div class="flex flex-wrap items-center gap-4">
      <!-- Map Selection -->
      <div class="flex items-center gap-2">
        <label for="map-select" class="text-sm font-medium text-gray-300">Map:</label>
        <select
          id="map-select"
          class="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-purple-500"
          value={draftState.map_name || ""}
          onchange={handleMapChange}
        >
          <option value="">Select Map...</option>
          {#each MAPS as map}
            <option value={map.id}>{map.name}</option>
          {/each}
        </select>
      </div>

      <!-- First Pick Configuration -->
      <button
        onclick={toggleFirstPick}
        disabled={draftState.my_team_picks.length > 0 || draftState.enemy_picks.length > 0 || draftState.my_team_bans.length > 0 || draftState.enemy_bans.length > 0}
        class="btn btn-outline btn-sm font-medium"
      >
        First Pick: <span class={draftState.my_team_first ? "text-cyan-400" : "text-rose-400"}>{draftState.my_team_first ? "Ally" : "Enemy"}</span>
      </button>

      <!-- System Actions -->
      <div class="h-6 w-px bg-gray-800"></div>
      
      <button
        onclick={undoLast}
        disabled={draftState.my_team_picks.length === 0 && draftState.enemy_picks.length === 0 && draftState.my_team_bans.length === 0 && draftState.enemy_bans.length === 0}
        class="btn btn-outline btn-sm font-medium"
      >
        Undo
      </button>

      <button
        onclick={resetDraft}
        class="btn btn-error btn-outline btn-sm font-medium"
      >
        Reset
      </button>

      <button
        onclick={reloadDB}
        class="btn btn-outline btn-sm font-medium"
      >
        Reload DB
      </button>
    </div>
  </header>

  <!-- Main Roster & Picks Grid -->
  <div class="grid grid-cols-1 xl:grid-cols-4 gap-6 flex-1">
    
    <!-- LEFT PANEL: MY TEAM (Ally) -->
    <div class="xl:col-span-1 flex flex-col gap-4">
      <div class="glass-panel p-4 flex flex-col gap-4 flex-1">
        <h2 class="text-cyan-400 font-bold border-b border-cyan-500/20 pb-2 flex justify-between items-center">
          <span>ALLY TEAM</span>
          <span class="text-xs bg-cyan-950/60 text-cyan-300 px-2 py-0.5 rounded-full border border-cyan-800/30">Picks</span>
        </h2>
                <!-- Picks slots -->
        <div class="flex flex-col gap-3 flex-1 justify-around">
          {#each Array(5) as _, i}
            {@const heroId = draftState.my_team_picks[i]}
            {@const isCurrentTurn = !draftState.is_complete && draftState.current_step && draftState.current_step.team === "my_team" && draftState.current_step.action === "pick" && draftState.my_team_picks.length === i}
            <div 
              role="presentation"
              onmouseenter={() => heroId && (inspectedHeroId = heroId)}
              class="flex items-center gap-3 p-2.5 rounded-lg bg-gray-900/40 border {isCurrentTurn ? 'active-turn-ally border-cyan-400' : 'border-gray-800/80'} h-[72px] {heroId ? 'cursor-pointer' : ''}"
            >
              {#if heroId}
                {@const hero = getHero(heroId)}
                <div class="relative h-12 w-12 rounded bg-gray-800 overflow-hidden border border-cyan-500/30">
                  <img
                    src="{backendUrl}/data/portraits/{heroId}.png"
                    alt={hero.name}
                    class="h-full w-full object-cover"
                    onerror={(e) => { e.currentTarget.style.display='none'; e.currentTarget.nextElementSibling.style.display='flex'; }}
                  />
                  <div class="hidden absolute inset-0 flex items-center justify-center bg-cyan-950 font-bold text-cyan-200">
                    {getRoleAbbreviation(hero.role)}
                  </div>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="font-bold text-white text-sm truncate">{hero.name}</div>
                  <div class="text-xs text-cyan-400">{hero.role}</div>
                </div>
              {:else}
                <div class="h-12 w-12 rounded border-2 border-dashed border-gray-800 flex items-center justify-center text-gray-600 font-bold">
                  {i + 1}
                </div>
                <div class="text-xs text-gray-500 font-medium">
                  {isCurrentTurn ? 'Selecting Hero...' : 'Empty Slot'}
                </div>
              {/if}
            </div>
          {/each}
        </div>

        <!-- Bans bar -->
        <div class="mt-4 border-t border-gray-800/80 pt-4">
          <h3 class="text-xs font-bold text-cyan-500/70 mb-2">ALLY BANS</h3>
          <div class="grid grid-cols-3 gap-2">
            {#each Array(3) as _, i}
              {@const heroId = draftState.my_team_bans[i]}
              {@const isCurrentTurn = !draftState.is_complete && draftState.current_step && draftState.current_step.team === "my_team" && draftState.current_step.action === "ban" && draftState.my_team_bans.length === i}
              <div 
                role="presentation"
                onmouseenter={() => heroId && (inspectedHeroId = heroId)}
                class="aspect-square rounded bg-gray-950/60 border {isCurrentTurn ? 'active-turn-ally border-cyan-400' : 'border-gray-850'} flex flex-col items-center justify-center relative overflow-hidden {heroId ? 'cursor-pointer' : ''}"
              >
                {#if heroId}
                  {@const hero = getHero(heroId)}
                  <img
                    src="{backendUrl}/data/portraits/{heroId}.png"
                    alt={hero.name}
                    class="h-full w-full object-cover opacity-60 grayscale"
                    onerror={(e) => { e.currentTarget.style.display='none'; e.currentTarget.nextElementSibling.style.display='flex'; }}
                  />
                  <div class="hidden absolute inset-0 flex items-center justify-center bg-cyan-950/80 font-bold text-xs text-cyan-300">
                    {getRoleAbbreviation(hero.role)}
                  </div>
                  <span class="absolute bottom-0 inset-x-0 bg-black/70 text-[9px] py-0.5 text-center text-cyan-200 truncate">{hero.name}</span>
                {:else}
                  <span class="text-[10px] text-gray-600 font-bold">{isCurrentTurn ? 'BAN' : i+1}</span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      </div>
    </div>

    <!-- MIDDLE PANEL: HERO SELECTOR -->
    <div class="xl:col-span-2 flex flex-col gap-4">
      <div class="glass-panel p-4 flex flex-col gap-4 flex-1">
        
        <!-- Filter Search Row -->
        <div class="flex flex-col md:flex-row gap-3">
          <label class="input input-bordered flex items-center gap-2 bg-gray-900 focus-within:input-primary w-full flex-1">
            <span class="text-gray-500 text-sm">🔍</span>
            <input
              type="text"
              placeholder="Search hero..."
              bind:value={searchQuery}
              class="grow bg-transparent border-none outline-none focus:ring-0 focus:outline-none text-white h-full"
            />
          </label>

          <!-- Role Filter -->
          <select
            bind:value={selectedRole}
            class="select select-bordered bg-gray-900 text-white focus:select-primary"
          >
            <option value="All">All Roles</option>
            <option value="Tank">Tanks</option>
            <option value="Bruiser">Bruisers</option>
            <option value="Healer">Healers</option>
            <option value="Ranged Assassin">Ranged Assassins</option>
            <option value="Melee Assassin">Melee Assassins</option>
            <option value="Support">Supports</option>
          </select>

          <!-- Tag Filter -->
          <select
            bind:value={selectedTag}
            class="select select-bordered bg-gray-900 text-white focus:select-primary"
          >
            {#each allTags as tag}
              <option value={tag}>{tag === "All" ? "All Tags" : tag}</option>
            {/each}
          </select>
        </div>

        <!-- Current Draft Status Banner -->
        <div class="bg-gray-900/60 border border-gray-800 rounded-lg p-3 text-center text-sm font-medium">
          {#if draftState.is_complete}
            <span class="text-purple-400 font-bold">Draft Complete! Ready to battle.</span>
          {:else if draftState.current_step}
            {@const step = draftState.current_step}
            <span>
              Current Turn: 
              <span class={step.team === 'my_team' ? 'text-cyan-400 font-bold' : 'text-rose-400 font-bold'}>
                {step.team === 'my_team' ? 'ALLY' : 'ENEMY'}
              </span> 
              to 
              <span class="uppercase font-bold {step.action === 'ban' ? 'text-amber-500' : 'text-purple-400'}">
                {step.action}
              </span>
            </span>
          {:else}
            <span class="text-gray-400">Loading draft state...</span>
          {/if}
        </div>

        <!-- Grid -->
        <div class="flex-1 overflow-y-auto pr-1 min-h-[400px] max-h-[600px]">
          {#if filteredHeroes.length === 0}
            <div class="h-full flex items-center justify-center text-gray-500 text-sm">
              No heroes match filters.
            </div>
          {:else}
            <div class="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-3">
              {#each filteredHeroes as hero}
                <button
                  onclick={() => selectHero(hero.id)}
                  onmouseenter={() => inspectedHeroId = hero.id}
                  disabled={draftState.is_complete}
                  class="group flex flex-col items-center gap-1.5 p-1 bg-gray-900/30 hover:bg-gray-800/40 disabled:opacity-50 disabled:hover:bg-transparent rounded-lg border border-gray-800/80 hover:border-purple-500/50 transition duration-200"
                >
                  <div class="aspect-square w-full rounded bg-gray-850 overflow-hidden relative border {hero.recommended_ban ? 'border-red-650 ring-1 ring-red-600/40' : 'border-gray-800'} group-hover:border-purple-500/30">
                    <img
                      src="{backendUrl}/data/portraits/{hero.id}.png"
                      alt={hero.name}
                      class="h-full w-full object-cover group-hover:scale-105 transition"
                      onerror={(e) => { e.currentTarget.style.display='none'; e.currentTarget.nextElementSibling.style.display='flex'; }}
                    />
                    <div class="hidden absolute inset-0 flex items-center justify-center bg-gray-900 font-bold text-sm text-gray-400">
                      {getRoleAbbreviation(hero.role)}
                    </div>
                    
                    <!-- Tier Badge overlay -->
                    <span class="absolute top-1 left-1 text-[9px] px-1 rounded font-bold border shadow-md
                      {hero.tier === 'S' ? 'bg-amber-500 text-black border-amber-300' : 
                       hero.tier === 'A' ? 'bg-purple-600 text-white border-purple-400' :
                       hero.tier === 'B' ? 'bg-blue-600 text-white border-blue-400' :
                       hero.tier === 'C' ? 'bg-gray-600 text-gray-200 border-gray-500' :
                       'bg-rose-950 text-rose-300 border-rose-800'}"
                    >
                      {hero.tier}
                    </span>

                    <!-- Recommended Ban Warning -->
                    {#if hero.recommended_ban}
                      <span class="absolute top-1 right-1 bg-red-600 text-white text-[8px] font-extrabold px-1 rounded border border-red-400 shadow-md">
                        BAN
                      </span>
                    {/if}
                  </div>
                  <span class="text-[10px] font-semibold text-gray-300 group-hover:text-white truncate w-full text-center px-1">
                    {hero.name}
                  </span>
                </button>
              {/each}
            </div>
          {/if}
        </div>

      </div>
    </div>

    <!-- RIGHT PANEL: RECOMMENDATIONS -->
    <div class="xl:col-span-1 flex flex-col gap-4">
      <div class="glass-panel p-4 flex flex-col gap-4 flex-1">
        <h2 class="text-purple-400 font-bold border-b border-purple-500/20 pb-2 flex justify-between items-center">
          <span>RECOMMENDATIONS</span>
          <span class="text-xs bg-purple-950/60 text-purple-300 px-2 py-0.5 rounded-full border border-purple-800/30">AI Scoring</span>
        </h2>

        <!-- Tabs -->
        <div class="tabs tabs-boxed bg-gray-950/60 grid grid-cols-2 p-1 border border-gray-855">
          <button 
            onclick={() => activeRecTab = "picks"}
            class="tab tab-sm font-semibold {activeRecTab === 'picks' ? 'tab-active bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'}"
          >
            Picks Suggestions
          </button>
          <button 
            onclick={() => activeRecTab = "bans"}
            class="tab tab-sm font-semibold {activeRecTab === 'bans' ? 'tab-active bg-red-600 text-white' : 'text-gray-400 hover:text-gray-200'}"
          >
            Bans Suggestions
          </button>
        </div>

        <!-- Score board -->
        <div class="flex-1 overflow-y-auto pr-1 flex flex-col gap-3 max-h-[320px] min-h-[200px]">
          {#if draftState.is_complete}
            <div class="h-full flex items-center justify-center text-center text-gray-500 text-sm p-4">
              Draft is complete. Recommendations disabled.
            </div>
          {:else}
            {@const currentList = activeRecTab === "picks" ? recommendations : banRecommendations}
            {#if currentList.length === 0}
              <div class="h-full flex items-center justify-center text-center text-gray-500 text-sm p-4">
                {activeRecTab === 'picks' ? 'Add heroes to see pick recommendations.' : 'Add heroes to see ban recommendations.'}
              </div>
            {:else}
              {#each currentList.slice(0, 8) as rec, index}
                {@const hero = getHero(rec.hero_id)}
                <div 
                  role="presentation"
                  onmouseenter={() => inspectedHeroId = rec.hero_id}
                  class="p-3 rounded-lg bg-gray-900/60 border border-gray-800 flex flex-col gap-2 {activeRecTab === 'picks' ? 'hover:border-purple-500/30' : 'hover:border-red-500/30'} transition cursor-pointer"
                >
                  <div class="flex items-center gap-3">
                    <!-- Rank number -->
                    <div class="h-6 w-6 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-xs font-bold {index === 0 ? (activeRecTab === 'picks' ? 'text-amber-400 border-amber-500/40' : 'text-red-400 border-red-500/40') : 'text-gray-400'}">
                      #{index + 1}
                    </div>
                    
                    <!-- Portrait -->
                    <div class="relative h-10 w-10 rounded bg-gray-850 overflow-hidden border {activeRecTab === 'picks' ? 'border-purple-500/20' : 'border-red-500/20'}">
                      <img
                        src="{backendUrl}/data/portraits/{rec.hero_id}.png"
                        alt={hero.name}
                        class="h-full w-full object-cover"
                        onerror={(e) => { e.currentTarget.style.display='none'; e.currentTarget.nextElementSibling.style.display='flex'; }}
                      />
                      <div class="hidden absolute inset-0 flex items-center justify-center bg-purple-950/80 font-bold text-xs {activeRecTab === 'picks' ? 'text-purple-300' : 'text-red-300'}">
                        {getRoleAbbreviation(hero.role)}
                      </div>
                    </div>

                    <!-- Name and Role -->
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-1.5">
                        <span class="font-bold text-white text-sm truncate">{hero.name}</span>
                        
                        <!-- Tier badge -->
                        <span class="text-[8px] font-extrabold px-1 rounded border shadow-sm
                          {hero.tier === 'S' ? 'bg-amber-500 text-black border-amber-300' : 
                           hero.tier === 'A' ? 'bg-purple-600 text-white border-purple-400' :
                           hero.tier === 'B' ? 'bg-blue-600 text-white border-blue-400' :
                           hero.tier === 'C' ? 'bg-gray-600 text-gray-200 border-gray-550' :
                           'bg-rose-950 text-rose-300 border-rose-800'}"
                        >
                          {hero.tier}
                        </span>
                      </div>
                      <div class="text-xs text-gray-400">{hero.role}</div>
                    </div>

                    <!-- Score -->
                    <div class="text-right">
                      <div class="text-sm font-bold {activeRecTab === 'picks' ? 'text-purple-400' : 'text-red-400'}">{rec.score}</div>
                      <div class="text-[9px] text-gray-500">score</div>
                    </div>
                  </div>

                  <!-- Reasons list -->
                  {#if rec.reasons && rec.reasons.length > 0}
                    <div class="border-t border-gray-850 pt-2 flex flex-col gap-1">
                      {#each rec.reasons as reason}
                        <div class="text-[10px] text-gray-400 flex items-start gap-1">
                          <span class={activeRecTab === 'picks' ? 'text-purple-400' : 'text-red-400'}>•</span>
                          <span>{reason}</span>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          {/if}
        </div>
      </div>

      <!-- Hero Details / Inspector Card -->
      <div class="glass-panel p-4 flex flex-col gap-3 min-h-[350px]">
        {#if !inspectedHero}
          <div class="h-full flex flex-col items-center justify-center text-center text-gray-500 text-sm p-4 flex-1">
            <span>Hover over any hero card to inspect builds, maps, and matchups.</span>
          </div>
        {:else}
          {@const activeBuild = (inspectedHero.talent_builds && inspectedHero.talent_builds.length > 0) ? (inspectedHero.talent_builds[selectedBuildIdx] || inspectedHero.talent_builds[0]) : null}
          {@const strongMaps = Object.entries(inspectedHero.map_performance).filter(([_, mod]) => mod > 1.0).map(([mapName]) => mapName)}
          {@const weakMaps = Object.entries(inspectedHero.map_performance).filter(([_, mod]) => mod < 1.0).map(([mapName]) => mapName)}
          <div class="flex items-center justify-between border-b border-gray-800 pb-2">
            <div class="flex items-center gap-2">
              <div class="relative h-9 w-9 rounded bg-gray-850 overflow-hidden border border-purple-500/20">
                <img
                  src="{backendUrl}/data/portraits/{inspectedHero.id}.png"
                  alt={inspectedHero.name}
                  class="h-full w-full object-cover"
                />
              </div>
              <div>
                <h3 class="font-bold text-white text-sm flex items-center gap-1.5">
                  {inspectedHero.name}
                  <span class="text-[8px] font-extrabold px-1 rounded border shadow-sm
                    {inspectedHero.tier === 'S' ? 'bg-amber-500 text-black border-amber-300' : 
                     inspectedHero.tier === 'A' ? 'bg-purple-600 text-white border-purple-400' :
                     inspectedHero.tier === 'B' ? 'bg-blue-600 text-white border-blue-400' :
                     inspectedHero.tier === 'C' ? 'bg-gray-600 text-gray-200 border-gray-550' :
                     'bg-rose-950 text-rose-300 border-rose-800'}"
                  >
                    {inspectedHero.tier}
                  </span>
                </h3>
                <span class="text-[10px] text-gray-400">{inspectedHero.role}</span>
              </div>
            </div>
            
            {#if inspectedHero.recommended_ban}
              <span class="bg-red-950 text-red-300 text-[8px] font-extrabold px-1.5 py-0.5 rounded border border-red-800 shadow-md">
                RECOMMENDED BAN
              </span>
            {/if}
          </div>

          <!-- Inspector Tabs/Grid -->
          <div class="flex-1 flex flex-col gap-2 overflow-y-auto pr-1">
            <!-- Talent Builds -->
            {#if inspectedHero.talent_builds && inspectedHero.talent_builds.length > 0}
              <div class="flex flex-col gap-1.5">
                <div class="flex items-center justify-between">
                  <span class="text-[10px] font-bold text-purple-400 uppercase tracking-wider">TALENT BUILD</span>
                  {#if inspectedHero.talent_builds.length > 1}
                    <select
                      bind:value={selectedBuildIdx}
                      class="bg-gray-900 border border-gray-800 rounded px-1.5 py-0.5 text-[10px] text-gray-300 focus:outline-none"
                    >
                      {#each inspectedHero.talent_builds as build, idx}
                        <option value={idx}>{build.name}</option>
                      {/each}
                    </select>
                  {:else}
                    <span class="text-[9px] text-gray-500">{inspectedHero.talent_builds[0].name}</span>
                  {/if}
                </div>

                <div class="grid grid-cols-7 gap-1 bg-gray-950/40 p-1.5 rounded-lg border border-gray-850">
                  {#each activeBuild.talents as talent}
                    <div class="flex flex-col items-center gap-0.5 text-center group/talent relative">
                      <span class="text-[8px] font-bold text-gray-500">Lvl {talent.level}</span>
                      <div class="h-6 w-6 rounded bg-gray-900 border border-gray-800 flex items-center justify-center text-[9px] font-bold text-gray-300 overflow-hidden cursor-pointer hover:border-purple-500 transition shadow-inner">
                        <span class="truncate px-0.5">{talent.name.substring(0, 3)}</span>
                      </div>
                      
                      <!-- Tooltip with full talent name -->
                      <div class="absolute bottom-full mb-1 hidden group-hover/talent:block bg-gray-900 border border-gray-700 text-white text-[9px] py-1 px-1.5 rounded shadow-xl whitespace-nowrap z-50">
                        {talent.name}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Map Performance -->
            {#if strongMaps.length > 0 || weakMaps.length > 0}
              <div class="grid grid-cols-2 gap-2 text-[10px] mt-1">
                <!-- Strong Maps -->
                {#if strongMaps.length > 0}
                  <div class="flex flex-col gap-1">
                    <span class="font-bold text-emerald-400 uppercase tracking-wider text-[9px]">Strong Maps</span>
                    <div class="flex flex-col gap-0.5 text-gray-350">
                      {#each strongMaps.slice(0, 3) as mapName}
                        <div class="flex items-center gap-1">
                          <span class="text-emerald-500">▲</span>
                          <span class="truncate">{MAPS.find(m => m.id === mapName)?.name || mapName.replace('_', ' ')}</span>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}

                <!-- Weak Maps -->
                {#if weakMaps.length > 0}
                  <div class="flex flex-col gap-1">
                    <span class="font-bold text-rose-400 uppercase tracking-wider text-[9px]">Weak Maps</span>
                    <div class="flex flex-col gap-0.5 text-gray-350">
                      {#each weakMaps.slice(0, 3) as mapName}
                        <div class="flex items-center gap-1">
                          <span class="text-rose-500">▼</span>
                          <span class="truncate">{MAPS.find(m => m.id === mapName)?.name || mapName.replace('_', ' ')}</span>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}
              </div>
            {/if}

            <!-- Matchups (Synergies & Counters) -->
            <div class="grid grid-cols-2 gap-2 text-[10px] border-t border-gray-850 pt-2 mt-1">
              <!-- Synergies -->
              <div class="flex flex-col gap-1">
                <span class="font-bold text-cyan-400 uppercase tracking-wider text-[9px]">Synergizes With</span>
                {#if inspectedHero.synergies.length > 0}
                  <div class="flex flex-wrap gap-1">
                    {#each inspectedHero.synergies.slice(0, 4) as synId}
                      {@const synHero = getHero(synId)}
                      <div role="presentation" class="group/syn relative h-5 w-5 rounded bg-gray-900 border border-gray-800 overflow-hidden cursor-pointer animate-fade-in" onmouseenter={() => inspectedHeroId = synId}>
                        <img src="{backendUrl}/data/portraits/{synId}.png" alt={synHero.name} class="h-full w-full object-cover" />
                        <div class="absolute bottom-full mb-1 hidden group-hover/syn:block bg-gray-900 border border-gray-700 text-white text-[9px] py-1 px-1.5 rounded shadow-xl whitespace-nowrap z-50">
                          {synHero.name}
                        </div>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <span class="text-gray-500 text-[9px]">No specific synergies</span>
                {/if}
              </div>

              <!-- Counters -->
              <div class="flex flex-col gap-1">
                <span class="font-bold text-amber-500 uppercase tracking-wider text-[9px]">Countered By</span>
                {#if inspectedHero.counters.length > 0}
                  <div class="flex flex-wrap gap-1">
                    {#each inspectedHero.counters.slice(0, 4) as cntId}
                      {@const cntHero = getHero(cntId)}
                      <div role="presentation" class="group/cnt relative h-5 w-5 rounded bg-gray-900 border border-gray-800 overflow-hidden cursor-pointer" onmouseenter={() => inspectedHeroId = cntId}>
                        <img src="{backendUrl}/data/portraits/{cntId}.png" alt={cntHero.name} class="h-full w-full object-cover" />
                        <div class="absolute bottom-full mb-1 hidden group-hover/cnt:block bg-gray-900 border border-gray-700 text-white text-[9px] py-1 px-1.5 rounded shadow-xl whitespace-nowrap z-50">
                          {cntHero.name}
                        </div>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <span class="text-gray-500 text-[9px]">No specific counters</span>
                {/if}
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>

  </div>

  <!-- BOTTOM BAR: ENEMY DRAFT STATE -->
  <div class="glass-panel p-4 flex flex-col gap-4">
    <h2 class="text-rose-400 font-bold border-b border-rose-500/20 pb-2 flex justify-between items-center">
      <span>ENEMY TEAM</span>
      <span class="text-xs bg-rose-950/60 text-rose-300 px-2 py-0.5 rounded-full border border-rose-800/30">Picks</span>
    </h2>
    <!-- Enemy picks -->
    <div class="grid grid-cols-5 gap-3">
      {#each Array(5) as _, i}
        {@const heroId = draftState.enemy_picks[i]}
        {@const isCurrentTurn = !draftState.is_complete && draftState.current_step && draftState.current_step.team === "enemy" && draftState.current_step.action === "pick" && draftState.enemy_picks.length === i}
        <div 
          role="presentation"
          onmouseenter={() => heroId && (inspectedHeroId = heroId)}
          class="flex items-center gap-3 p-2.5 rounded-lg bg-gray-900/40 border {isCurrentTurn ? 'active-turn-enemy border-rose-400' : 'border-gray-855'} h-[72px] {heroId ? 'cursor-pointer' : ''}"
        >
          {#if heroId}
            {@const hero = getHero(heroId)}
            <div class="relative h-12 w-12 rounded bg-gray-800 overflow-hidden border border-rose-500/30">
              <img
                src="{backendUrl}/data/portraits/{heroId}.png"
                alt={hero.name}
                class="h-full w-full object-cover"
                onerror={(e) => { e.currentTarget.style.display='none'; e.currentTarget.nextElementSibling.style.display='flex'; }}
              />
              <div class="hidden absolute inset-0 flex items-center justify-center bg-rose-950 font-bold text-rose-200">
                {getRoleAbbreviation(hero.role)}
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-bold text-white text-sm truncate">{hero.name}</div>
              <div class="text-xs text-rose-400">{hero.role}</div>
            </div>
          {:else}
            <div class="h-12 w-12 rounded border-2 border-dashed border-gray-855 flex items-center justify-center text-gray-700 font-bold">
              {i + 1}
            </div>
            <div class="text-xs text-gray-500 font-medium">
              {isCurrentTurn ? 'Selecting Hero...' : 'Empty Slot'}
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <!-- Enemy bans -->
    <div class="border-t border-gray-800/80 pt-4 flex flex-col md:flex-row gap-4 items-start md:items-center">
      <h3 class="text-xs font-bold text-rose-500/70 whitespace-nowrap">ENEMY BANS</h3>
      <div class="flex gap-2 flex-wrap">
        {#each Array(3) as _, i}
          {@const heroId = draftState.enemy_bans[i]}
          {@const isCurrentTurn = !draftState.is_complete && draftState.current_step && draftState.current_step.team === "enemy" && draftState.current_step.action === "ban" && draftState.enemy_bans.length === i}
          <div 
            role="presentation"
            onmouseenter={() => heroId && (inspectedHeroId = heroId)}
            class="h-14 w-14 rounded bg-gray-950/60 border {isCurrentTurn ? 'active-turn-enemy border-rose-400' : 'border-gray-855'} flex flex-col items-center justify-center relative overflow-hidden {heroId ? 'cursor-pointer' : ''}"
          >
            {#if heroId}
              {@const hero = getHero(heroId)}
              <img
                src="{backendUrl}/data/portraits/{heroId}.png"
                alt={hero.name}
                class="h-full w-full object-cover opacity-60 grayscale"
                onerror={(e) => { e.currentTarget.style.display='none'; e.currentTarget.nextElementSibling.style.display='flex'; }}
              />
              <div class="hidden absolute inset-0 flex items-center justify-center bg-rose-950/80 font-bold text-xs text-rose-300">
                {getRoleAbbreviation(hero.role)}
              </div>
              <span class="absolute bottom-0 inset-x-0 bg-black/70 text-[9px] py-0.5 text-center text-rose-200 truncate">{hero.name}</span>
            {:else}
              <span class="text-[10px] text-gray-600 font-bold">{isCurrentTurn ? 'BAN' : i+1}</span>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  </div>
</main>
