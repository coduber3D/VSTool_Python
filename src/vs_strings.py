HUD_TEXT = """
        🖱 Camera Controls

        LMB ------------------ Orbit
        Shift + LMB ---------- Pan
        MMB ----------------- Dolly
        Wheel --------------- Zoom
        Ctrl + Wheel -------- FOV

        W/A/S/D ----------- Move Camera
        Q/E ----------------- Up/Down
        H -------------------- Hide HUD
        F ------------------Frame Scene
        G -------------First person camera"""


BG_SHADER_VERTEX = """#version 330 core
                out vec2 v_uv;
                
                void main()
                {
                    vec2 pos = vec2(
                        (gl_VertexID << 1) & 2,
                        gl_VertexID & 2
                    );
                
                    v_uv = pos;
                    gl_Position = vec4(pos * 7.5 - 1.0, 0.0, 1.0);
                }"""
BG_SHADER_FRAG = """#version 330 core
                in vec2 v_uv;
                out vec4 FragColor;
                uniform float u_time;
                
                uniform sampler2D u_bgTexture;
                
                void main()
                {
                    vec2 uv = v_uv * 4.0;               // tile amount
                    vec4 tex = texture(u_bgTexture, uv);
                    tex = tex + clamp(tex.b * sin(u_time*0.2),-0.1,0.5);
                    // subtle vignette
                    float d = distance(v_uv, vec2(0.5));
                    tex.rgb *= smoothstep(0.8, 0.4, d);
                
                    FragColor = tex;
                }"""

ASSET_SHADER_VERTEX = """
            #version 330 core

            layout (location = 0) in vec3 position;
            layout (location = 1) in vec2 texcoord;
            layout (location = 2) in vec4 color;
            
            /* --- Skinning attributes --- */
            layout (location = 3) in ivec4 bone_ids;
            layout (location = 4) in vec4 bone_weights;
            
            /* --- Uniforms --- */
            uniform mat4 u_mvp;
            uniform mat4 u_bones[100];
            uniform bool u_use_skinning;
            
            /* --- Outputs --- */
            out vec2 v_uv;
            out vec4 v_color;
            
            void main()
            {
                vec4 pos = vec4(position, 1.0);
            
                if (u_use_skinning)
                {
                    mat4 skin =
                        bone_weights.x * u_bones[bone_ids.x] +
                        bone_weights.y * u_bones[bone_ids.y] +
                        bone_weights.z * u_bones[bone_ids.z] +
                        bone_weights.w * u_bones[bone_ids.w];
            
                    pos = skin * pos;
                }
            
                v_uv = texcoord;
                v_color = color;
                gl_Position = u_mvp * pos;
            }
            """
ASSET_SHADER_FRAG = """
            #version 330 core

            in vec2 v_uv;
            in vec4 v_color;
            out vec4 FragColor;
            uniform bool u_hasUV;
            
            uniform sampler2D u_texture;
            
            uniform float u_time;
            uniform float u_scanlineIntensity;
            uniform float u_scanlineCount;
            uniform bool  u_useVertexColor;
            
            uniform bool  u_disableTexture;
            
            void main()
            {
                vec4 texel = vec4(1.0);
                
                if (u_disableTexture)
                {
                    vec2 new_uv = vec2(v_uv.x, 1.0 - v_uv.y);
                    texel = texture(u_texture, new_uv);
                    
                    if (texel.a < 0.5)
                        discard;
                }
                vec3 color = texel.rgb;
            
                if (u_useVertexColor)
                    color *= (v_color.rgb * 2.0);
            
                // Scanlines
                float scan = sin(gl_FragCoord.y * u_scanlineCount * 0.01);
                scan = mix(1.0, scan, u_scanlineIntensity);
                color *= scan;
            
                FragColor = vec4(color, texel.a * v_color.a);
            }
            """